package process

import (
	"sync"
	"time"
)

type Source string

const (
	SourceHytale     Source = "hytale"
	SourceGradle     Source = "gradle"
	SourceVite       Source = "vite"
	SourceLicense    Source = "license"
	SourceMaster     Source = "master"
	SourceMasterVite Source = "master-vite"
	SourceDeploy     Source = "deploy"
	SourceVPS        Source = "vps"
	SourceSystem     Source = "system"
)

type LogLine struct {
	Time    time.Time
	Source  Source
	Text    string
	IsError bool
}

// RingBuffer is a thread-safe ring buffer for log lines.
type RingBuffer struct {
	mu    sync.RWMutex
	lines []LogLine
	cap   int
	head  int
	count int
}

func NewRingBuffer(capacity int) *RingBuffer {
	return &RingBuffer{
		lines: make([]LogLine, capacity),
		cap:   capacity,
	}
}

func (rb *RingBuffer) Add(line LogLine) {
	rb.mu.Lock()
	defer rb.mu.Unlock()
	rb.lines[rb.head] = line
	rb.head = (rb.head + 1) % rb.cap
	if rb.count < rb.cap {
		rb.count++
	}
}

func (rb *RingBuffer) Lines() []LogLine {
	rb.mu.RLock()
	defer rb.mu.RUnlock()
	result := make([]LogLine, rb.count)
	start := rb.head - rb.count
	if start < 0 {
		start += rb.cap
	}
	for i := 0; i < rb.count; i++ {
		result[i] = rb.lines[(start+i)%rb.cap]
	}
	return result
}

func (rb *RingBuffer) FilterBySource(source Source) []LogLine {
	rb.mu.RLock()
	defer rb.mu.RUnlock()
	var result []LogLine
	start := rb.head - rb.count
	if start < 0 {
		start += rb.cap
	}
	for i := 0; i < rb.count; i++ {
		line := rb.lines[(start+i)%rb.cap]
		if line.Source == source {
			result = append(result, line)
		}
	}
	return result
}

func (rb *RingBuffer) Clear() {
	rb.mu.Lock()
	defer rb.mu.Unlock()
	rb.head = 0
	rb.count = 0
}

func (rb *RingBuffer) Count() int {
	rb.mu.RLock()
	defer rb.mu.RUnlock()
	return rb.count
}
