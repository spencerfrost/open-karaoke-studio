# openkaraoke/gui_components/file_browser.py
"""Component definition for the file browser section."""

import PySimpleGUI as sg

def layout():
    """Returns the layout list for the file browser row."""
    return [
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