# openkaraoke/app.py
"""Contains the main application class, orchestrating GUI and audio processing."""

import threading
from pathlib import Path
import PySimpleGUI as sg

from openkaraoke.audio_processing import process_audio_thread
from . import gui
from . import demucs_processor
from . import file_manager
from . import config

class App:
    """Main application class for Open Karaoke Studio."""

    def __init__(self):
        self.processing_thread = None
        self.stop_event = threading.Event()
        self.window = None

    def run(self):
        """Runs the main application loop."""

        demucs_ok = demucs_processor.is_available()
        self.window = gui.create_main_window(demucs_ok)

        if demucs_ok:
            gui.update_song_list(self.window, file_manager.get_processed_songs())

        while True:
            event, values = self.window.read()

            if event == sg.WIN_CLOSED or event == "Exit":
                if self.processing_thread is not None and self.processing_thread.is_alive():
                    print("Warning: Closing window while processing is active.")
                break

            self.handle_event(event, values, demucs_ok)

        self.cleanup()

    def handle_event(self, event, values, demucs_ok):
        """Handles GUI events."""

        if event == "-FILEPATH-" and demucs_ok:
            self.handle_filepath_event(values["-FILEPATH-"])

        elif event == "-PROCESS-" and demucs_ok:
            self.handle_process_event(values["-FILEPATH-"])

        elif event == "-THREAD_UPDATE-":
            gui.update_status(self.window, values[event])

        elif event == "-REFRESH_SONGS-":
            gui.update_song_list(self.window, file_manager.get_processed_songs())

        elif event == "-THREAD_DONE-":
            self.handle_thread_done_event()
            
        elif event == "-STOP-" and self.processing_thread is not None and self.processing_thread.is_alive():
            self.handle_stop_event()

        elif event == "-SONG_LIST-":
            self.handle_song_list_event(values["-SONG_LIST-"])

    def handle_filepath_event(self, filepath):
        """Handles the -FILEPATH- event."""
        if filepath and Path(filepath).is_file():
            gui.update_process_button(self.window, disabled=False)
            gui.update_status(self.window, "Ready to process")
        else:
            gui.update_process_button(self.window, disabled=True)
            gui.update_status(self.window, config.DEFAULT_STATUS_SELECT_FILE)

    def handle_process_event(self, filepath_str):
        """Handles the -PROCESS- event."""

        if not filepath_str or not Path(filepath_str).is_file():
            gui.update_status(
                self.window, "** Error: Please select a valid audio file first! **"
            )
            return
        if self.processing_thread is not None and self.processing_thread.is_alive():
            sg.popup_error("Processing already in progress!", title="Busy")
            return

        gui.update_process_button(self.window, disabled=True)
        gui.update_stop_button(self.window, disabled=False)
        gui.update_status(self.window, "Starting processing thread...")
        self.stop_event.clear()  # Ensure the stop event is clear before starting
        self.processing_thread = threading.Thread(
            target=process_audio_thread,
            args=(filepath_str, self.window, self.stop_event),
            daemon=True,
        )
        self.processing_thread.start()

    def handle_thread_done_event(self):
        """Handles the -THREAD_DONE- event."""
        gui.update_process_button(self.window, disabled=False)
        gui.update_stop_button(self.window, disabled=True)
        self.processing_thread = None
        self.stop_event.clear() # Ensure the stop event is clear after thread finishes

    def handle_stop_event(self):
        """Handles the -STOP- event."""
        gui.update_status(self.window, "Requesting to stop processing...")
        self.stop_event.set()

    def handle_song_list_event(self, selected_songs):
        """Handles the -SONG_LIST- event."""
        if selected_songs:
            selected_song = selected_songs[0]
            gui.update_status(self.window, f"Selected song: {selected_song}")

    def cleanup(self):
        """Cleans up resources before exiting."""
        if self.window:
            self.window.close()