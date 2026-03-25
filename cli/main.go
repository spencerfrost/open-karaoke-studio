package main

import (
	"fmt"
	"log"
	"os"
	"path/filepath"

	tea "github.com/charmbracelet/bubbletea"
	"oks-cli/internal/app"
	"oks-cli/internal/config"
	"oks-cli/internal/service"
	"oks-cli/process"
)

func main() {
	// Determine config file path: same directory as executable, named oks-dev.yaml
	execPath, err := os.Executable()
	if err != nil {
		log.Fatalf("get executable path: %v", err)
	}
	configDir := filepath.Dir(execPath)
	configPath := filepath.Join(configDir, "oks-dev.yaml")

	// Load config via config.Load — auto-creates with defaults if missing
	cfg, err := config.Load(configPath)
	if err != nil {
		log.Fatalf("load config: %v", err)
	}

	// If ProjectRoot is empty, detect it
	if cfg.ProjectRoot == "" {
		cfg.ProjectRoot = config.DetectProjectRoot()
		if cfg.ProjectRoot == "" {
			fmt.Fprintln(os.Stderr, "error: could not detect project root (no pyproject.toml found)")
			os.Exit(1)
		}
	}

	// If HostIP is empty, detect it
	if cfg.HostIP == "" {
		cfg.HostIP = config.DetectHostIP()
	}

	// Create process.Manager
	manager := process.NewManager(cfg.LogBuffer)

	// Create and register all 4 services
	manager.Register(service.NewBackend(cfg.ProjectRoot))
	manager.Register(service.NewCelery(cfg.ProjectRoot))
	manager.Register(service.NewFrontend(cfg.ProjectRoot, cfg.BuildFrontend))
	manager.Register(service.NewDocs(cfg.ProjectRoot))

	// Auto-start services listed in cfg.AutoStart
	for _, name := range cfg.AutoStart {
		p := manager.Get(name)
		if p == nil {
			continue
		}
		if err := p.Start(); err != nil {
			fmt.Fprintf(os.Stderr, "warning: failed to start %s: %v\n", name, err)
		}
	}

	// Create TUI model
	model := app.New(manager, cfg)

	// Run BubbleTea program
	program := tea.NewProgram(model, tea.WithAltScreen())
	if _, err := program.Run(); err != nil {
		log.Fatalf("tui: %v", err)
	}
}
