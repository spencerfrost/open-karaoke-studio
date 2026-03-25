package process

import (
	"sync"
	"time"
)

type Manager struct {
	mu     sync.RWMutex
	procs  []*Process // ordered slice
	names  map[string]int
	logBuf *RingBuffer
}

func NewManager(logBufSize int) *Manager {
	return &Manager{
		names:  make(map[string]int),
		logBuf: NewRingBuffer(logBufSize),
	}
}

func (m *Manager) Register(p *Process) {
	p.SetLogHandler(func(line LogLine) {
		m.logBuf.Add(line)
	})
	m.mu.Lock()
	defer m.mu.Unlock()
	if idx, ok := m.names[p.Name]; ok {
		// Replace existing (stop old first)
		old := m.procs[idx]
		if old.Status() == StatusRunning {
			_ = old.Stop()
		}
		m.procs[idx] = p
	} else {
		m.names[p.Name] = len(m.procs)
		m.procs = append(m.procs, p)
	}
}

func (m *Manager) Get(name string) *Process {
	m.mu.RLock()
	defer m.mu.RUnlock()
	if idx, ok := m.names[name]; ok {
		return m.procs[idx]
	}
	return nil
}

func (m *Manager) All() []*Process {
	m.mu.RLock()
	defer m.mu.RUnlock()
	out := make([]*Process, len(m.procs))
	copy(out, m.procs)
	return out
}

func (m *Manager) LogBuffer() *RingBuffer {
	return m.logBuf
}

func (m *Manager) StopAll() {
	m.mu.RLock()
	defer m.mu.RUnlock()
	for _, p := range m.procs {
		if p.Status() == StatusRunning {
			_ = p.Stop()
		}
	}
}

func (m *Manager) AnyRunning() bool {
	m.mu.RLock()
	defer m.mu.RUnlock()
	for _, p := range m.procs {
		if p.Status() == StatusRunning {
			return true
		}
	}
	return false
}

func (m *Manager) RunningCount() (running int, total int) {
	m.mu.RLock()
	defer m.mu.RUnlock()
	total = len(m.procs)
	for _, p := range m.procs {
		if p.Status() == StatusRunning {
			running++
		}
	}
	return
}

func (m *Manager) SystemLog(text string) {
	m.logBuf.Add(LogLine{
		Time:   time.Now(),
		Source: SourceSystem,
		Text:   text,
	})
}

func (m *Manager) Log(source Source, text string) {
	m.logBuf.Add(LogLine{
		Time:   time.Now(),
		Source: source,
		Text:   text,
	})
}
