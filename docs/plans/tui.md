Build a Go TUI dev tool for Open Karaoke Studio, modeled after the BubbleTea/Lipgloss pattern. I've already copied `process/process.go`, `process/manager.go`, and the ring buffer/output files into `cli/internal/process/`. Build everything else needed to make a working TUI.

**Project layout to create:**
```
cli/
├── main.go
├── go.mod                 (module: github.com/YOUR_ORG/oks-cli)
├── go.sum
└── internal/
    ├── config/config.go
    ├── service/           (backend.go, celery.go, frontend.go, docs.go)
    ├── theme/theme.go
    └── app/app.go
```

**The 4 services to manage** (map these exactly):

| ID | Name | Dir | Command |
|---|---|---|---|
| 0 | Backend | `{projectRoot}/backend` | `./run_api.sh` (Shell: true) |
| 1 | Celery | `{projectRoot}/backend` | `./run_celery.sh` (Shell: true) |
| 2 | Frontend | `{projectRoot}/frontend` | dev: `pnpm run host` / build: `pnpm run build && pnpm run preview --host 0.0.0.0 --port 5192` (Shell: true) |
| 3 | Docs | `{projectRoot}/docs` | `pnpm run dev --host 0.0.0.0 --port 5194 --strictPort` (Shell: true) |

**Config struct** (YAML file `oks-dev.yaml`, auto-created next to binary with defaults, auto-detects project root by walking up looking for `pyproject.toml` or `backend/` directory):
```go
type Config struct {
    ProjectRoot   string     `yaml:"projectRoot"`
    HostIP        string     `yaml:"hostIP"`        // empty = auto-detect via net.InterfaceAddrs
    BuildFrontend bool       `yaml:"buildFrontend"` // false = dev mode
    Ports         PortConfig `yaml:"ports"`
    AutoStart     []string   `yaml:"autoStart"`     // default: ["backend", "celery", "frontend"]
    LogBuffer     int        `yaml:"logBufferSize"` // default: 5000
}
type PortConfig struct {
    API           int `yaml:"api"`           // 5123
    FrontendDev   int `yaml:"frontendDev"`   // 5193
    FrontendBuild int `yaml:"frontendBuild"` // 5192
    Docs          int `yaml:"docs"`          // 5194
}
```

**IP detection** — use `net.InterfaceAddrs()` to find the first non-loopback IPv4 address (replacing the `ip addr show | grep | awk` pipeline in the old bash script).

**TUI behavior:**
- Use `tea.WithAltScreen()` and a tick every 500ms to refresh uptimes
- Tab 0 = Overview: table of all 4 services (name, status dot, uptime, PID), then a URL panel below showing `http://{hostIP}:{port}` for each service
- Tabs 1-4 = per-service log view with scroll (`j`/`k` or arrow keys), auto-scroll to bottom when new output arrives, `s` to toggle auto-scroll
- Keybindings: `tab`/`1`-`4` to switch tabs, `enter`/`space` on overview row to start/stop service, `b` on overview to toggle build mode and restart frontend, `q` to quit (with confirm if any service running), `ctrl+c` to force quit
- On quit: call `manager.StopAll()` before exiting, send graceful stop to backend/celery (write `\n` then kill after 5s), just kill frontend/docs immediately
- Status indicators: `●` green=running, yellow=starting/stopping, red=failed, dim=stopped

**Source constants** to add to the copied process/output.go (or wherever LogLine/Source is defined):
```go
const (
    SourceSystem   Source = iota
    SourceBackend
    SourceCelery
    SourceFrontend
    SourceDocs
)
```

**go.mod dependencies needed:** `github.com/charmbracelet/bubbletea`, `github.com/charmbracelet/lipgloss`, `gopkg.in/yaml.v3`

**Do not** create a Makefile, README, or any docs. Just the Go source files. After writing all files, run `go mod tidy` and `go build ./...` to verify it compiles.
