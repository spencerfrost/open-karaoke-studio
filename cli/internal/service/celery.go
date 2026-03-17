package service

import (
	"path/filepath"

	"oks-cli/process"
)

func NewCelery(root string) *process.Process {
	return process.NewShell("celery", process.SourceCelery,
		filepath.Join(root, "backend"),
		"./run_celery.sh", nil)
}
