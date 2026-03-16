package process

import (
	"bufio"
	"fmt"
	"io"
	"os/exec"
	"runtime"
	"sync"
	"time"
)

type Status int

const (
	StatusStopped Status = iota
	StatusStarting
	StatusRunning
	StatusStopping
	StatusFailed
)

func (s Status) String() string {
	switch s {
	case StatusStopped:
		return "stopped"
	case StatusStarting:
		return "starting"
	case StatusRunning:
		return "running"
	case StatusStopping:
		return "stopping"
	case StatusFailed:
		return "failed"
	default:
		return "unknown"
	}
}

type Process struct {
	Name    string
	Source  Source
	Dir     string
	Command string
	Args    []string
	Env     []string
	Shell   bool // If true, wrap with cmd /c on Windows (for .bat/.cmd/npm)

	cmd     *exec.Cmd
	stdin   io.WriteCloser
	status  Status
	pid     int
	started time.Time
	err     error
	mu      sync.RWMutex
	onLog   func(LogLine)
}

func New(name string, source Source, dir, command string, args []string) *Process {
	return &Process{
		Name:    name,
		Source:  source,
		Dir:     dir,
		Command: command,
		Args:    args,
		status:  StatusStopped,
	}
}

func NewShell(name string, source Source, dir, command string, args []string) *Process {
	return &Process{
		Name:    name,
		Source:  source,
		Dir:     dir,
		Command: command,
		Args:    args,
		Shell:   true,
		status:  StatusStopped,
	}
}

func (p *Process) SetLogHandler(fn func(LogLine)) {
	p.mu.Lock()
	defer p.mu.Unlock()
	p.onLog = fn
}

func (p *Process) Status() Status {
	p.mu.RLock()
	defer p.mu.RUnlock()
	return p.status
}

func (p *Process) PID() int {
	p.mu.RLock()
	defer p.mu.RUnlock()
	return p.pid
}

func (p *Process) StartedAt() time.Time {
	p.mu.RLock()
	defer p.mu.RUnlock()
	return p.started
}

func (p *Process) Uptime() time.Duration {
	p.mu.RLock()
	defer p.mu.RUnlock()
	if p.status != StatusRunning || p.started.IsZero() {
		return 0
	}
	return time.Since(p.started)
}

func (p *Process) Error() error {
	p.mu.RLock()
	defer p.mu.RUnlock()
	return p.err
}

func (p *Process) Start() error {
	p.mu.Lock()
	if p.status == StatusRunning || p.status == StatusStarting {
		p.mu.Unlock()
		return fmt.Errorf("%s is already running", p.Name)
	}
	p.status = StatusStarting
	p.err = nil
	p.mu.Unlock()

	p.log(fmt.Sprintf("Starting %s...", p.Name), false)

	var cmd *exec.Cmd
	if runtime.GOOS == "windows" && p.Shell {
		// Shell wrapping needed for batch scripts (gradlew.bat, npm.cmd)
		cmd = exec.Command("cmd", append([]string{"/c", p.Command}, p.Args...)...)
	} else {
		cmd = exec.Command(p.Command, p.Args...)
	}
	cmd.Dir = p.Dir
	if len(p.Env) > 0 {
		cmd.Env = append(cmd.Environ(), p.Env...)
	}

	stdout, err := cmd.StdoutPipe()
	if err != nil {
		p.setFailed(err)
		return err
	}
	stderr, err := cmd.StderrPipe()
	if err != nil {
		p.setFailed(err)
		return err
	}
	stdin, err := cmd.StdinPipe()
	if err != nil {
		p.setFailed(err)
		return err
	}

	if err := cmd.Start(); err != nil {
		p.setFailed(err)
		return err
	}

	p.mu.Lock()
	p.cmd = cmd
	p.stdin = stdin
	p.pid = cmd.Process.Pid
	p.started = time.Now()
	p.status = StatusRunning
	p.mu.Unlock()

	p.log(fmt.Sprintf("%s started (PID %d)", p.Name, cmd.Process.Pid), false)

	go p.pipeOutput(stdout, false)
	go p.pipeOutput(stderr, true)
	go p.waitForExit()

	return nil
}

func (p *Process) Stop() error {
	p.mu.Lock()
	if p.status != StatusRunning {
		p.mu.Unlock()
		return fmt.Errorf("%s is not running", p.Name)
	}
	p.status = StatusStopping
	cmd := p.cmd
	stdin := p.stdin
	p.mu.Unlock()

	p.log(fmt.Sprintf("Stopping %s...", p.Name), false)

	// For Hytale server, send "stop" command first
	if p.Source == SourceHytale && stdin != nil {
		_, _ = io.WriteString(stdin, "stop\n")
		// Give it a moment to shut down gracefully
		done := make(chan struct{})
		go func() {
			cmd.Wait()
			close(done)
		}()
		select {
		case <-done:
			p.mu.Lock()
			p.status = StatusStopped
			p.mu.Unlock()
			p.log(fmt.Sprintf("%s stopped gracefully", p.Name), false)
			return nil
		case <-time.After(10 * time.Second):
		}
	}

	if cmd.Process != nil {
		_ = cmd.Process.Kill()
	}

	p.mu.Lock()
	p.status = StatusStopped
	p.mu.Unlock()
	p.log(fmt.Sprintf("%s stopped", p.Name), false)
	return nil
}

func (p *Process) WriteStdin(s string) error {
	p.mu.RLock()
	stdin := p.stdin
	p.mu.RUnlock()
	if stdin == nil {
		return fmt.Errorf("no stdin available")
	}
	_, err := io.WriteString(stdin, s)
	return err
}

func (p *Process) pipeOutput(r io.Reader, isErr bool) {
	scanner := bufio.NewScanner(r)
	scanner.Buffer(make([]byte, 0, 64*1024), 1024*1024)
	for scanner.Scan() {
		p.log(scanner.Text(), isErr)
	}
}

func (p *Process) waitForExit() {
	if p.cmd == nil {
		return
	}
	err := p.cmd.Wait()
	p.mu.Lock()
	if p.status == StatusStopping {
		p.status = StatusStopped
	} else if err != nil {
		p.status = StatusFailed
		p.err = err
	} else {
		p.status = StatusStopped
	}
	p.mu.Unlock()

	if err != nil {
		p.log(fmt.Sprintf("%s exited with error: %v", p.Name, err), true)
	} else {
		p.log(fmt.Sprintf("%s exited", p.Name), false)
	}
}

func (p *Process) setFailed(err error) {
	p.mu.Lock()
	p.status = StatusFailed
	p.err = err
	p.mu.Unlock()
	p.log(fmt.Sprintf("Failed to start %s: %v", p.Name, err), true)
}

// SetRunning marks this process as running externally.
func (p *Process) SetRunning() {
	p.mu.Lock()
	p.status = StatusRunning
	p.started = time.Now()
	p.mu.Unlock()
}

// SetStopped marks this process as stopped externally.
func (p *Process) SetStopped() {
	p.mu.Lock()
	p.status = StatusStopped
	p.mu.Unlock()
}

// SetFailed marks this process as failed externally.
func (p *Process) SetFailed(err error) {
	p.mu.Lock()
	p.status = StatusFailed
	p.err = err
	p.mu.Unlock()
}

func (p *Process) log(text string, isErr bool) {
	p.mu.RLock()
	fn := p.onLog
	p.mu.RUnlock()
	if fn != nil {
		fn(LogLine{
			Time:    time.Now(),
			Source:  p.Source,
			Text:    text,
			IsError: isErr,
		})
	}
}
