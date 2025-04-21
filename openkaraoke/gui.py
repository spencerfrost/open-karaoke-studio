# gui.py
"""Defines the PySimpleGUI layout using components and tabs,
and creates the main window"""

import sys
import PySimpleGUI as sg
from . import config

try:
    from .gui_components import file_browser, action_status, song_library
except ImportError:
    print("Error: Could not import GUI components.", file=sys.stderr)
    sys.exit(1)


def create_main_window(demucs_available):
    """Creates and returns the main application window with tabs."""

    sg.theme("DarkBlue3")

    # --- Define Tab Layouts ---

    # Layout for the first tab (Processing & Library)
    # We'll reuse the components we created earlier
    processing_tab_layout = [
        file_browser.layout(),
        # Note: Action/Status row is kept *outside* the tabs below
        #       Alternatively, put action_status.layout() here if you
        #       want it specific to this tab.
        [sg.HorizontalSeparator()],
        song_library.layout(),
    ]

    # Layout for the second tab (Placeholder)
    settings_tab_layout = [ # Example name
        [sg.Text("Placeholder Tab 1 Content")],
        [sg.Text("Settings or other features will go here.")],
        [sg.Input(key="-PLACEHOLDER_INPUT-")], # Example element
    ]

    # Layout for the third tab (Placeholder)
    player_tab_layout = [ # Example name
        [sg.Text("Placeholder Tab 2 Content")],
        [sg.Text("The Karaoke Player interface will go here.")],
        [sg.Button("Play (Placeholder)", key="-PLAY_PLACEHOLDER-")], # Example element
    ]


    # --- Assemble Main Layout with TabGroup ---

    # Error layout if Demucs isn't available (no tabs needed here)
    if not demucs_available:
        layout = [
            [sg.Text("Demucs or PyTorch failed to import.")],
            [sg.Text("Karaoke features disabled. Check console.")],
            [sg.Text(f"Python path: {sys.executable}")],
            [sg.Button("Exit")],
        ]
    else:
        # Define the TabGroup
        tab_group_layout = [
             [sg.Tab('Process & Library', processing_tab_layout, key='-TAB_PROCESS-'),
              sg.Tab('Placeholder 1', settings_tab_layout, key='-TAB_PLACEHOLDER1-'),
              sg.Tab('Placeholder 2', player_tab_layout, key='-TAB_PLACEHOLDER2-')]
        ]

        # Assemble the final window layout
        layout = [
            [sg.Text(config.WINDOW_TITLE, font="_ 18")],
            [sg.HorizontalSeparator()],
            # Place the action/status row *above* the tabs for global controls/status
            action_status.layout(),
            [sg.HorizontalSeparator()],
            # Add the TabGroup
            [sg.TabGroup(tab_group_layout, enable_events=True, key='-TAB_GROUP-')],
            # Status bar could also go here if preferred, below tabs
        ]

    # Create the window
    # Make it slightly larger perhaps to accommodate tabs comfortably
    window = sg.Window(config.WINDOW_TITLE, layout, finalize=True, resizable=True, size=(750, 450))
    return window

# --- GUI Update Functions ---
# (These functions remain the same as they operate on the window object
# and element keys. Ensure keys like '-STATUS-', '-PROCESS-', '-STOP-',
# '-SONG_LIST-' exist in the layout, which they currently do in the
# action_status component and processing tab.)

def update_status(window: sg.Window, message: str):
    """Updates the status text element."""
    if window and '-STATUS-' in window.key_dict: # Check if element exists
        window["-STATUS-"].update(f"Status: {message}")

def update_process_button(window: sg.Window, disabled: bool):
    """Enables or disables the main process button."""
    if window and '-PROCESS-' in window.key_dict:
        window["-PROCESS-"].update(disabled=disabled)

def update_stop_button(window: sg.Window, disabled: bool):
    """Enables or disables the stop button."""
    if window and '-STOP-' in window.key_dict:
        window["-STOP-"].update(disabled=disabled)

def update_song_list(window: sg.Window, song_list: list):
    """Updates the song listbox."""
    if window and '-SONG_LIST-' in window.key_dict:
        window["-SONG_LIST-"].update(values=song_list)