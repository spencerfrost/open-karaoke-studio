package app

import (
	"fmt"
	"strings"
	"time"

	"github.com/charmbracelet/bubbles/table"
	"github.com/charmbracelet/bubbles/viewport"
	tea "github.com/charmbracelet/bubbletea"
	"oks-cli/internal/config"
	"oks-cli/internal/service"
	"oks-cli/internal/theme"
	"oks-cli/process"
)

type tickMsg time.Time

type logLineMsg struct {
	idx  int    // service index 0-3
	text string // formatted log line
}

// Model is the root BubbleTea model for the TUI dev tool.
type Model struct {
	manager     *process.Manager
	cfg         *config.Config
	activeTab   int // 0=overview, 1-4=service logs (1=backend, 2=celery, 3=frontend, 4=docs)
	table       table.Model
	viewports   [4]viewport.Model
	autoScroll  [4]bool
	buildMode   bool
	confirmQuit bool
	width       int
	height      int
	// map from process.Source to viewport index (0-3)
	sourceIdx map[process.Source]int
	// accumulated log text per service
	content [4]string
	// channel for log lines delivered from background goroutines
	logCh chan logLineMsg
}

// New constructs the TUI model, wires up log handlers, and initialises bubbles components.
func New(manager *process.Manager, cfg *config.Config) Model {
	sourceIdx := map[process.Source]int{
		process.SourceBackend:  0,
		process.SourceCelery:   1,
		process.SourceFrontend: 2,
		process.SourceDocs:     3,
	}

	logCh := make(chan logLineMsg, 1000)

	// Register log handlers for each process.
	for _, p := range manager.All() {
		p := p // capture
		idx, ok := sourceIdx[p.Source]
		if !ok {
			continue
		}
		p.SetLogHandler(func(line process.LogLine) {
			text := fmt.Sprintf("[%s] %s", line.Time.Format("15:04:05"), line.Text)
			select {
			case logCh <- logLineMsg{idx: idx, text: text}:
			default:
				// drop if channel full
			}
		})
	}

	// Initialise table.
	columns := []table.Column{
		{Title: "NAME", Width: 12},
		{Title: "STATUS", Width: 18},
		{Title: "UPTIME", Width: 10},
		{Title: "PID", Width: 8},
	}
	t := table.New(
		table.WithColumns(columns),
		table.WithFocused(true),
	)
	s := table.DefaultStyles()
	s.Header = theme.TableHeader
	s.Selected = theme.TableRowSelected
	t.SetStyles(s)

	// Initialise viewports with placeholder size.
	var viewports [4]viewport.Model
	for i := range viewports {
		viewports[i] = viewport.New(80, 20)
	}

	var autoScroll [4]bool
	for i := range autoScroll {
		autoScroll[i] = true
	}

	return Model{
		manager:    manager,
		cfg:        cfg,
		activeTab:  0,
		table:      t,
		viewports:  viewports,
		autoScroll: autoScroll,
		sourceIdx:  sourceIdx,
		logCh:      logCh,
	}
}

// Init starts the BubbleTea program.
func (m Model) Init() tea.Cmd {
	return tea.Batch(tea.EnterAltScreen, tickCmd())
}

func tickCmd() tea.Cmd {
	return tea.Tick(500*time.Millisecond, func(t time.Time) tea.Msg {
		return tickMsg(t)
	})
}

// Update processes messages and returns the updated model plus any commands.
func (m Model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {

	case tea.WindowSizeMsg:
		m.width = msg.Width
		m.height = msg.Height

		// Resize table: show up to numServices+2 rows, min header
		numServices := len(m.manager.All())
		tableHeight := numServices + 2
		if tableHeight > 10 {
			tableHeight = 10
		}
		m.table.SetHeight(tableHeight)
		m.table.SetRows(buildTableRows(m.manager))

		// Resize viewports: leave room for tab bar (1), header (2), help (1), padding (4)
		vpHeight := m.height - 8
		if vpHeight < 1 {
			vpHeight = 1
		}
		for i := range m.viewports {
			m.viewports[i].Width = m.width
			m.viewports[i].Height = vpHeight
			// Re-set content so viewport re-renders at new size.
			m.viewports[i].SetContent(m.content[i])
		}

	case tickMsg:
		// Drain log channel.
	drainLoop:
		for {
			select {
			case lm := <-m.logCh:
				idx := lm.idx
				if m.content[idx] == "" {
					m.content[idx] = lm.text
				} else {
					m.content[idx] = capLines(m.content[idx]+"\n"+lm.text, 5000)
				}
				m.viewports[idx].SetContent(m.content[idx])
				if m.autoScroll[idx] {
					m.viewports[idx].GotoBottom()
				}
			default:
				break drainLoop
			}
		}
		// Refresh table rows.
		m.table.SetRows(buildTableRows(m.manager))
		return m, tickCmd()

	case tea.KeyMsg:
		// Confirm-quit overlay intercepts y / n / esc.
		if m.confirmQuit {
			switch msg.String() {
			case "y":
				m.manager.StopAll()
				return m, tea.Quit
			case "n", "esc":
				m.confirmQuit = false
			}
			return m, nil
		}

		switch msg.String() {
		case "ctrl+c":
			// Force quit without stopping services — intentional emergency exit.
			return m, tea.Quit

		case "tab":
			m.activeTab = (m.activeTab + 1) % 5

		case "1":
			m.activeTab = 0
		case "2":
			m.activeTab = 1
		case "3":
			m.activeTab = 2
		case "4":
			m.activeTab = 3
		case "5":
			m.activeTab = 4

		case "enter", " ":
			if m.activeTab == 0 {
				sel := m.table.Cursor()
				procs := m.manager.All()
				if sel >= 0 && sel < len(procs) {
					p := procs[sel]
					switch p.Status() {
					case process.StatusRunning:
						go p.Stop() //nolint:errcheck
					case process.StatusStopped, process.StatusFailed:
						go p.Start() //nolint:errcheck
					// StatusStarting and StatusStopping: do nothing (already in transition)
					}
				}
			}

		case "b":
			if m.activeTab == 0 {
				var wasRunning bool
				if old := m.manager.Get("frontend"); old != nil {
					wasRunning = old.Status() == process.StatusRunning
				}
				m.buildMode = !m.buildMode
				buildMode := m.buildMode
				root := m.cfg.ProjectRoot
				logCh := m.logCh
				idx := m.sourceIdx[process.SourceFrontend]
				go func() {
					newFrontend := service.NewFrontend(root, buildMode)
					m.manager.Register(newFrontend)
					// Re-attach TUI log handler (Register overwrites with ring-buffer handler).
					newFrontend.SetLogHandler(func(line process.LogLine) {
						text := fmt.Sprintf("[%s] %s", line.Time.Format("15:04:05"), line.Text)
						select {
						case logCh <- logLineMsg{idx: idx, text: text}:
						default:
						}
					})
					if wasRunning {
						_ = newFrontend.Start()
					}
				}()
			}

		case "s":
			if m.activeTab >= 1 && m.activeTab <= 4 {
				i := m.activeTab - 1
				m.autoScroll[i] = !m.autoScroll[i]
				if m.autoScroll[i] {
					m.viewports[i].GotoBottom()
				}
			}

		case "j", "down":
			if m.activeTab >= 1 && m.activeTab <= 4 {
				m.viewports[m.activeTab-1].LineDown(1)
				m.autoScroll[m.activeTab-1] = false
			}

		case "k", "up":
			if m.activeTab >= 1 && m.activeTab <= 4 {
				m.viewports[m.activeTab-1].LineUp(1)
				m.autoScroll[m.activeTab-1] = false
			}

		case "pgdown":
			if m.activeTab >= 1 && m.activeTab <= 4 {
				m.viewports[m.activeTab-1].HalfViewDown()
				m.autoScroll[m.activeTab-1] = false
			}

		case "pgup":
			if m.activeTab >= 1 && m.activeTab <= 4 {
				m.viewports[m.activeTab-1].HalfViewUp()
				m.autoScroll[m.activeTab-1] = false
			}

		case "q":
			if m.manager.AnyRunning() {
				m.confirmQuit = true
			} else {
				m.manager.StopAll()
				return m, tea.Quit
			}
		}

		// Forward arrow keys to table when on overview tab.
		if m.activeTab == 0 {
			switch msg.String() {
			case "up", "k", "down", "j":
				var cmd tea.Cmd
				m.table, cmd = m.table.Update(msg)
				return m, cmd
			}
		}
	}

	return m, nil
}

// View renders the current tab.
func (m Model) View() string {
	if m.activeTab == 0 {
		return renderOverview(m)
	}
	return renderLogView(m, m.activeTab-1)
}

// capLines trims s to at most maxLines lines, keeping the most recent ones.
func capLines(s string, maxLines int) string {
	if s == "" {
		return s
	}
	count := strings.Count(s, "\n") + 1
	if count <= maxLines {
		return s
	}
	skip := count - maxLines
	for i := 0; i < len(s); i++ {
		if s[i] == '\n' {
			skip--
			if skip == 0 {
				return s[i+1:]
			}
		}
	}
	return s
}
