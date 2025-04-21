# gui.py
"""Defines the PySimpleGUI layout using components and creates the main window"""

import sys
import PySimpleGUI as sg
import config

from .gui_components import file_browser, action_status, song_library


def create_main_window(demucs_available):
    """Creates and returns the main application window using components."""

    sg.theme("DarkBlue3")

    if not demucs_available:
        layout = [
            [sg.Text("Demucs or PyTorch failed to import.")],
            [sg.Text("Karaoke features disabled. Check console.")],
            [sg.Text(f"Python path: {sys.executable}")],
            [sg.Button("Exit")],
        ]
    else:
        layout = [
            [sg.Text(config.WINDOW_TITLE, font="_ 18")],
            [sg.HorizontalSeparator()],
            file_browser.layout(),
            action_status.layout(),
            [sg.HorizontalSeparator()],
            song_library.layout(),
        ]

    window = sg.Window(config.WINDOW_TITLE, layout, finalize=True, resizable=True)
    return window


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
