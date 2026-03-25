package theme

import (
	"github.com/charmbracelet/lipgloss"
	"oks-cli/process"
)

// Status dots
func DotRunning() string {
	return lipgloss.NewStyle().
		Foreground(lipgloss.Color("#22c55e")).
		Render("●")
}

func DotStarting() string {
	return lipgloss.NewStyle().
		Foreground(lipgloss.Color("#eab308")).
		Render("●")
}

func DotStopping() string {
	return lipgloss.NewStyle().
		Foreground(lipgloss.Color("#eab308")).
		Render("●")
}

func DotFailed() string {
	return lipgloss.NewStyle().
		Foreground(lipgloss.Color("#ef4444")).
		Render("●")
}

func DotStopped() string {
	return lipgloss.NewStyle().
		Foreground(lipgloss.Color("#6b7280")).
		Render("○")
}

// StatusDot returns the appropriate dot for a given process status.
func StatusDot(s process.Status) string {
	switch s {
	case process.StatusRunning:
		return DotRunning()
	case process.StatusStarting:
		return DotStarting()
	case process.StatusStopping:
		return DotStopping()
	case process.StatusFailed:
		return DotFailed()
	case process.StatusStopped:
		return DotStopped()
	default:
		return DotStopped()
	}
}

// Styles
var (
	// Tab bar
	ActiveTab = lipgloss.NewStyle().
		Bold(true).
		Foreground(lipgloss.Color("#ffffff")).
		Underline(true)

	InactiveTab = lipgloss.NewStyle().
		Foreground(lipgloss.Color("#6b7280"))

	// Overview table
	TableHeader = lipgloss.NewStyle().
		Bold(true).
		Foreground(lipgloss.Color("#ffffff"))

	TableRow = lipgloss.NewStyle().
		Foreground(lipgloss.Color("#e5e7eb"))

	TableRowSelected = lipgloss.NewStyle().
		Bold(true).
		Foreground(lipgloss.Color("#ffffff")).
		Background(lipgloss.Color("#1d4ed8"))

	// URL panel
	URLLabel = lipgloss.NewStyle().
		Foreground(lipgloss.Color("#6b7280"))

	URLValue = lipgloss.NewStyle().
		Foreground(lipgloss.Color("#60a5fa"))

	// Help bar
	HelpKey = lipgloss.NewStyle().
		Foreground(lipgloss.Color("#6b7280"))

	HelpDesc = lipgloss.NewStyle().
		Foreground(lipgloss.Color("#9ca3af"))

	// Log view header
	LogHeader = lipgloss.NewStyle().
		Bold(true).
		Foreground(lipgloss.Color("#ffffff"))

	// Borders/panels
	Panel = lipgloss.NewStyle().
		Border(lipgloss.NormalBorder(), true).
		BorderForeground(lipgloss.Color("#374151"))
)
