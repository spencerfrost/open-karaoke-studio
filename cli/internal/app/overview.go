package app

import (
	"fmt"
	"strconv"
	"strings"
	"time"

	"github.com/charmbracelet/bubbles/table"
	"github.com/charmbracelet/lipgloss"
	"oks-cli/internal/theme"
	"oks-cli/process"
)

// renderOverview renders the full overview tab view.
func renderOverview(m Model) string {
	sections := []string{
		renderTabBar(m.activeTab),
		m.table.View(),
		renderURLPanel(m),
		renderHelpBar(),
	}
	if m.confirmQuit {
		sections = append(sections, renderQuitConfirm())
	}
	return lipgloss.JoinVertical(lipgloss.Left, sections...)
}

// renderTabBar renders the tab labels with active/inactive styling.
func renderTabBar(activeTab int) string {
	labels := []string{
		"[1] Overview",
		"[2] Backend",
		"[3] Celery",
		"[4] Frontend",
		"[5] Docs",
	}
	parts := make([]string, len(labels))
	for i, label := range labels {
		if i == activeTab {
			parts[i] = theme.ActiveTab.Render(label)
		} else {
			parts[i] = theme.InactiveTab.Render(label)
		}
	}
	return strings.Join(parts, "  ")
}

// renderURLPanel renders the service URL list.
func renderURLPanel(m Model) string {
	hostIP := m.cfg.HostIP
	if hostIP == "" {
		hostIP = "localhost"
	}

	apiPort := m.cfg.Ports.API
	var frontendPort int
	if m.buildMode {
		frontendPort = m.cfg.Ports.FrontendBuild
	} else {
		frontendPort = m.cfg.Ports.FrontendDev
	}
	docsPort := m.cfg.Ports.Docs

	lines := []string{
		fmt.Sprintf("%s  %s",
			theme.URLLabel.Render("Backend "),
			theme.URLValue.Render(fmt.Sprintf("http://%s:%d", hostIP, apiPort)),
		),
		fmt.Sprintf("%s  %s",
			theme.URLLabel.Render("Frontend"),
			theme.URLValue.Render(fmt.Sprintf("http://%s:%d", hostIP, frontendPort)),
		),
		fmt.Sprintf("%s  %s",
			theme.URLLabel.Render("Docs    "),
			theme.URLValue.Render(fmt.Sprintf("http://%s:%d", hostIP, docsPort)),
		),
	}
	return strings.Join(lines, "\n")
}

// renderHelpBar renders the keybinding hint line.
func renderHelpBar() string {
	pairs := []struct{ key, desc string }{
		{"enter/space", "start/stop"},
		{"b", "build mode"},
		{"tab/1-5", "switch"},
		{"q", "quit"},
	}
	parts := make([]string, len(pairs))
	for i, p := range pairs {
		parts[i] = theme.HelpKey.Render(p.key) + " " + theme.HelpDesc.Render(p.desc)
	}
	return strings.Join(parts, "  ")
}

// renderQuitConfirm renders the quit confirmation overlay.
func renderQuitConfirm() string {
	msg := lipgloss.NewStyle().
		Bold(true).
		Foreground(lipgloss.Color("#fbbf24")).
		Render("Quit? Services still running.") +
		"  " +
		theme.HelpKey.Render("[y]") + " " + theme.HelpDesc.Render("confirm") +
		"  " +
		theme.HelpKey.Render("[n]") + " " + theme.HelpDesc.Render("cancel")
	return lipgloss.NewStyle().
		Border(lipgloss.NormalBorder(), true).
		BorderForeground(lipgloss.Color("#fbbf24")).
		Padding(0, 1).
		Render(msg)
}

// buildTableRows builds table rows from the current process manager state.
func buildTableRows(manager *process.Manager) []table.Row {
	rows := []table.Row{}
	for _, p := range manager.All() {
		rows = append(rows, table.Row{
			p.Name,
			fmt.Sprintf("%s %s", theme.StatusDot(p.Status()), p.Status()),
			formatUptime(p.Uptime()),
			formatPID(p.PID()),
		})
	}
	return rows
}

// formatUptime returns "—" if the duration is zero, otherwise "H:MM:SS".
func formatUptime(d time.Duration) string {
	if d == 0 {
		return "—"
	}
	d = d.Round(time.Second)
	h := int(d.Hours())
	m := int(d.Minutes()) % 60
	s := int(d.Seconds()) % 60
	return fmt.Sprintf("%d:%02d:%02d", h, m, s)
}

// formatPID returns "—" if pid is 0, otherwise the PID as a string.
func formatPID(pid int) string {
	if pid == 0 {
		return "—"
	}
	return strconv.Itoa(pid)
}
