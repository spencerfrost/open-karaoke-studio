package service

import (
	"path/filepath"

	"oks-cli/process"
)

func NewDocs(root string) *process.Process {
	return process.NewShell("docs", process.SourceDocs,
		filepath.Join(root, "docs"),
		"pnpm run dev --host 0.0.0.0 --port 5194 --strictPort", nil)
}
