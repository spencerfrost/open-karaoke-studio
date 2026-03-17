package app

import (
	"fmt"
	"strings"

	"github.com/charmbracelet/lipgloss"
	"oks-cli/internal/theme"
)

// renderLogView renders the log tab for the given service index (0-3).
func renderLogView(m Model, idx int) string {
	procs := m.manager.All()
	if idx < 0 || idx >= len(procs) {
		return renderTabBar(idx+1) + "\n(no process)"
	}
	p := procs[idx]

	header := theme.LogHeader.Render(
		fmt.Sprintf("%s  %s  %s", p.Name, theme.StatusDot(p.Status()), formatUptime(p.Uptime())),
	)

	sections := []string{
		renderTabBar(idx + 1),
		header,
	}

	if !m.autoScroll[idx] {
		scrollHint := lipgloss.NewStyle().
			Foreground(lipgloss.Color("#6b7280")).
			Render("[auto-scroll paused — s to resume]")
		sections = append(sections, scrollHint)
	}

	sections = append(sections,
		m.viewports[idx].View(),
		renderLogHelpBar(),
	)

	return strings.Join(sections, "\n")
}

// renderLogHelpBar renders the help line shown in log tabs.
func renderLogHelpBar() string {
	pairs := []struct{ key, desc string }{
		{"j/k", "scroll"},
		{"s", "toggle auto-scroll"},
		{"tab/1-5", "switch"},
		{"q", "quit"},
	}
	parts := make([]string, len(pairs))
	for i, p := range pairs {
		parts[i] = theme.HelpKey.Render(p.key) + " " + theme.HelpDesc.Render(p.desc)
	}
	return strings.Join(parts, "  ")
}
