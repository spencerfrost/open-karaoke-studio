# openkaraoke/gui_components/song_library.py
"""Component definition for the song library listbox."""

import PySimpleGUI as sg


def layout():
    """Returns the layout list for the song browser section."""
    return [
        sg.Text("Processed Songs Library:", font="_ 14"),
        sg.Listbox(
            values=[],  # Initially empty
            key="-SONG_LIST-",
            enable_events=True,
            size=(60, 10),
            expand_x=True,
            expand_y=True,
        ),
    ]
