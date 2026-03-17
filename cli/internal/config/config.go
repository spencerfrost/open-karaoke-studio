package config

import (
	"fmt"
	"net"
	"os"
	"path/filepath"

	"gopkg.in/yaml.v3"
)

// PortConfig defines port mappings for all services.
type PortConfig struct {
	API           int `yaml:"api"`           // default: 5123
	FrontendDev   int `yaml:"frontendDev"`   // default: 5193
	FrontendBuild int `yaml:"frontendBuild"` // default: 5192
	Docs          int `yaml:"docs"`          // default: 5194
}

// Config holds the application configuration.
type Config struct {
	ProjectRoot   string     `yaml:"projectRoot"`
	HostIP        string     `yaml:"hostIP"`        // empty = auto-detect
	BuildFrontend bool       `yaml:"buildFrontend"` // false = dev mode
	Ports         PortConfig `yaml:"ports"`
	AutoStart     []string   `yaml:"autoStart"`     // default: ["backend", "celery", "frontend"]
	LogBuffer     int        `yaml:"logBufferSize"` // default: 5000
}

// DefaultConfig returns a Config with all defaults filled in.
func DefaultConfig() *Config {
	return &Config{
		ProjectRoot:   "",
		HostIP:        "",
		BuildFrontend: false,
		Ports: PortConfig{
			API:           5123,
			FrontendDev:   5193,
			FrontendBuild: 5192,
			Docs:          5194,
		},
		AutoStart: []string{"backend", "celery", "frontend"},
		LogBuffer: 5000,
	}
}

// Load reads a YAML config file from the given path.
// If the file does not exist, it writes defaults to the path and returns them.
// On other errors, it returns the error.
func Load(path string) (*Config, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		if os.IsNotExist(err) {
			// File doesn't exist, create it with defaults
			cfg := DefaultConfig()
			if err := Save(cfg, path); err != nil {
				return nil, fmt.Errorf("failed to write default config to %s: %w", path, err)
			}
			return cfg, nil
		}
		return nil, fmt.Errorf("failed to read config file %s: %w", path, err)
	}

	cfg := DefaultConfig()
	if err := yaml.Unmarshal(data, cfg); err != nil {
		return nil, fmt.Errorf("failed to parse config YAML: %w", err)
	}

	return cfg, nil
}

// Save marshals cfg to YAML and writes it to the given path.
func Save(cfg *Config, path string) error {
	data, err := yaml.Marshal(cfg)
	if err != nil {
		return fmt.Errorf("failed to marshal config to YAML: %w", err)
	}

	if err := os.MkdirAll(filepath.Dir(path), 0755); err != nil {
		return fmt.Errorf("failed to create config directory: %w", err)
	}

	if err := os.WriteFile(path, data, 0644); err != nil {
		return fmt.Errorf("failed to write config file %s: %w", path, err)
	}

	return nil
}

// DetectProjectRoot walks up from the current working directory looking for a directory
// containing pyproject.toml. Returns the first match, or empty string if not found.
// Walks up a maximum of 10 levels.
func DetectProjectRoot() string {
	dir, err := os.Getwd()
	if err != nil {
		return ""
	}
	for i := 0; i < 10; i++ {
		if _, err := os.Stat(filepath.Join(dir, "pyproject.toml")); err == nil {
			return dir
		}
		parent := filepath.Dir(dir)
		if parent == dir {
			break
		}
		dir = parent
	}
	return ""
}

// DetectHostIP finds the first non-loopback IPv4 address.
// Returns "127.0.0.1" as fallback if none found.
func DetectHostIP() string {
	addrs, err := net.InterfaceAddrs()
	if err != nil {
		return "127.0.0.1"
	}

	for _, addr := range addrs {
		ipNet, ok := addr.(*net.IPNet)
		if !ok {
			continue
		}

		ip := ipNet.IP.To4()
		if ip != nil && !ip.IsLoopback() {
			return ip.String()
		}
	}

	return "127.0.0.1"
}
