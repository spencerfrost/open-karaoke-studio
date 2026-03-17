package service

import (
	"path/filepath"

	"oks-cli/process"
)

func NewFrontend(root string, buildMode bool) *process.Process {
	if buildMode {
		return process.NewShell("frontend", process.SourceFrontend,
			filepath.Join(root, "frontend"),
			"pnpm run build && pnpm run preview --host 0.0.0.0 --port 5192", nil)
	}
	return process.NewShell("frontend", process.SourceFrontend,
		filepath.Join(root, "frontend"),
		"pnpm run host", nil)
}
