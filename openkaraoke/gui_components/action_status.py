# openkaraoke/gui_components/action_status.py
"""Component definition for the action buttons and status bar."""

import PySimpleGUI as sg
from . import config

def layout():
    """Returns the layout list for the action/status row."""
    return [
        sg.Button("Create Karaoke Tracks", key="-PROCESS-", disabled=True),
        sg.Button("Stop", key="-STOP-", disabled=True),
        sg.Text(
            config.DEFAULT_STATUS_SELECT_FILE,  # Or pass config value if preferred
            key="-STATUS-",
            size=(50, 1),
            expand_x=True,
        ),
    ]
