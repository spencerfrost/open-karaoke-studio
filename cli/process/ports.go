package process

import (
	"fmt"
	"net"
	"os/exec"
	"runtime"
	"strconv"
	"strings"
	"time"
)

func IsPortAvailable(port int) bool {
	// Try TCP on both IPv4 and IPv6 loopback
	for _, host := range []string{"127.0.0.1", "[::1]"} {
		addr := fmt.Sprintf("%s:%d", host, port)
		conn, err := net.DialTimeout("tcp", addr, 300*time.Millisecond)
		if err == nil {
			conn.Close()
			return false // Port in use
		}
	}
	// Try UDP
	udpAddr := fmt.Sprintf("127.0.0.1:%d", port)
	ln, err := net.ListenPacket("udp", udpAddr)
	if err != nil {
		return false // Can't bind = something is using it
	}
	ln.Close()
	return true // Nothing on TCP or UDP = port is free
}

func WaitForPort(port int, timeout time.Duration) bool {
	deadline := time.Now().Add(timeout)
	for time.Now().Before(deadline) {
		if !IsPortAvailable(port) {
			return true // Port became active
		}
		time.Sleep(250 * time.Millisecond)
	}
	return false
}

// FindPIDByPort returns the PID of the process listening on the given TCP port,
// or 0 if no process is found.
func FindPIDByPort(port int) int {
	if runtime.GOOS == "windows" {
		return findPIDWindows(port)
	}
	return findPIDUnix(port)
}

func findPIDWindows(port int) int {
	// netstat -ano outputs lines like:
	//   TCP    0.0.0.0:3000    0.0.0.0:0    LISTENING    12345
	out, err := exec.Command("cmd", "/c", "netstat", "-ano").Output()
	if err != nil {
		return 0
	}
	needle := fmt.Sprintf(":%d ", port)
	for _, line := range strings.Split(string(out), "\n") {
		line = strings.TrimSpace(line)
		if !strings.Contains(line, "LISTENING") {
			continue
		}
		if !strings.Contains(line, needle) {
			continue
		}
		// Last field is the PID
		fields := strings.Fields(line)
		if len(fields) < 5 {
			continue
		}
		pid, err := strconv.Atoi(fields[len(fields)-1])
		if err == nil && pid > 0 {
			return pid
		}
	}
	return 0
}

func findPIDUnix(port int) int {
	// lsof -ti :PORT returns PIDs, one per line
	out, err := exec.Command("lsof", "-ti", fmt.Sprintf(":%d", port)).Output()
	if err != nil {
		return 0
	}
	for _, line := range strings.Split(strings.TrimSpace(string(out)), "\n") {
		pid, err := strconv.Atoi(strings.TrimSpace(line))
		if err == nil && pid > 0 {
			return pid
		}
	}
	return 0
}

// KillPID forcefully kills a process by PID. Returns an error if it fails.
func KillPID(pid int) error {
	if pid <= 0 {
		return fmt.Errorf("invalid PID %d", pid)
	}
	if runtime.GOOS == "windows" {
		return exec.Command("taskkill", "/F", "/PID", strconv.Itoa(pid)).Run()
	}
	return exec.Command("kill", "-9", strconv.Itoa(pid)).Run()
}

// KillProcessOnPort finds and kills whatever is listening on the given port.
// Returns the killed PID, or 0 if nothing was found.
func KillProcessOnPort(port int) (int, error) {
	pid := FindPIDByPort(port)
	if pid == 0 {
		return 0, nil
	}
	return pid, KillPID(pid)
}
