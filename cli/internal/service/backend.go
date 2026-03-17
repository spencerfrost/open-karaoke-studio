package service

import (
	"path/filepath"

	"oks-cli/process"
)

func NewBackend(root string) *process.Process {
	return process.NewShell("backend", process.SourceBackend,
		filepath.Join(root, "backend"),
		"./run_api.sh", nil)
}
