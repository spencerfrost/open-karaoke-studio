# gui.py
"""Defines the PySimpleGUI layout and creates the main window"""

import PySimpleGUI as sg
import sys
import config  # Import settings


def create_main_window(demucs_available):  # Doesn't need initial_settings anymore
    """Creates and returns the main application window."""

    sg.theme("DarkBlue3")  # Example theme

    # Row 1: File Selection
    file_browser_row = [
        sg.Text("Audio File:"),
        sg.Input(key="-FILEPATH-", readonly=True, enable_events=True, expand_x=True),
        sg.FileBrowse(
            button_text="Browse",
            file_types=(
                ("Audio Files", "*.mp3 *.wav *.flac *.ogg *.m4a"),
                ("All Files", "*.*"),
            ),
        ),
    ]

    # Row 2: Action Buttons and Status
    action_row = [
        sg.Button("Create Karaoke Tracks", key="-PROCESS-", disabled=True),
        sg.Button("Stop", key="-STOP-", disabled=True),  # Add Stop button
        sg.Text(
            config.DEFAULT_STATUS_SELECT_FILE,
            key="-STATUS-",
            size=(50, 1),
            expand_x=True,
        ),
    ]

    # Row 3: Song Browser
    browser_row = [
        sg.Text("Processed Songs Library:", font="_ 14"),
        sg.Listbox(
            values=[],  # Initially empty
            key="-SONG_LIST-",
            enable_events=True,
            size=(60, 10),
            expand_x=True,
            expand_y=True,  # Allow vertical expansion
        ),
    ]

    # Combine layout (Single layout, no tabs)
    if not demucs_available:
        layout = [
            [sg.Text("Demucs or PyTorch failed to import.")],
            [
                sg.Text(
                    "Karaoke features disabled. Please check console output and installation."
                )
            ],
            [sg.Text(f"Attempted Python path: {sys.executable}")],
            [sg.Button("Exit")],
        ]
    else:
        layout = [
            [sg.Text(config.WINDOW_TITLE, font="_ 18")],
            [sg.HorizontalSeparator()],
            file_browser_row,
            action_row,
            [sg.HorizontalSeparator()],
            browser_row,
        ]

    # Create the window
    window = sg.Window(config.WINDOW_TITLE, layout, finalize=True, resizable=True)

    return window


# --- GUI Update Functions ---


def update_status(window: sg.Window, message: str):
    """Updates the status text element."""
    if window:
        window["-STATUS-"].update(f"Status: {message}")


def update_process_button(window: sg.Window, disabled: bool):
    """Enables or disables the main process button."""
    if window:
        window["-PROCESS-"].update(disabled=disabled)


def update_stop_button(window: sg.Window, disabled: bool):
    """Enables or disables the stop button."""
    if window:
        window["-STOP-"].update(disabled=disabled)


def update_song_list(window: sg.Window, song_list: list):
    """Updates the song listbox."""
    if window:
        window["-SONG_LIST-"].update(values=song_list)
