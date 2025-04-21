# main.py
"""Main application file for Open Karaoke Studio"""

import threading
import sys
import traceback
from pathlib import Path

import gui
import demucs_processor
import file_manager

import PySimpleGUI as sg
import config

PROCESSING_THREAD = None


def process_audio_thread(filepath_str, window):  # Simpler signature
    """Target function for the audio processing thread."""
    global PROCESSING_THREAD

    def gui_callback(message):
        """Function to send status updates back to the main thread."""
        if window:
            window.write_event_value("-THREAD_UPDATE-", message)

    try:
        filepath = Path(filepath_str)
        gui_callback(f"Starting processing for {filepath.name}...")

        # 1. Ensure library and create song directory (using default base path)
        file_manager.ensure_library_exists()
        song_dir = file_manager.get_song_dir(filepath)
        gui_callback(f"Using song directory: {song_dir}")

        # 2. Copy original file
        gui_callback("Copying original file...")
        original_saved_path = file_manager.save_original_file(filepath, song_dir)
        if not original_saved_path:
            gui_callback("** Error: Failed to copy original file. Aborting. **")
            return

        # 3. Separate audio (using hardcoded settings via demucs_processor)
        success = demucs_processor.separate_audio(filepath, song_dir, gui_callback)

        # 4. Final status update
        if success:
            gui_callback(f"Successfully processed {filepath.name}!")
            window.write_event_value("-REFRESH_SONGS-", None)
        else:
            gui_callback(f"Processing failed for {filepath.name}.")

    except Exception as e:
        print(f"Critical error in processing thread: {e}", file=sys.stderr)
        traceback.print_exc()
        gui_callback(f"** Critical Thread Error: {e} **")
    finally:
        if window:
            window.write_event_value("-THREAD_DONE-", None)


def main():
    """Main application function."""
    global PROCESSING_THREAD

    demucs_ok = demucs_processor.is_available()

    window = gui.create_main_window(demucs_ok)  # No initial settings needed

    if demucs_ok:
        gui.update_song_list(
            window, file_manager.get_processed_songs()
        )  # Uses default path

    # --- Event Loop ---
    while True:
        event, values = window.read()

        if event == sg.WIN_CLOSED or event == "Exit":
            if PROCESSING_THREAD is not None and PROCESSING_THREAD.is_alive():
                print("Warning: Closing window while processing is active.")
            break

        # --- GUI Event Handling ---

        if event == "-FILEPATH-" and demucs_ok:
            filepath = values["-FILEPATH-"]
            if filepath and Path(filepath).is_file():
                gui.update_process_button(window, disabled=False)
                gui.update_status(window, "Ready to process")
            else:
                gui.update_process_button(window, disabled=True)
                gui.update_status(window, config.DEFAULT_STATUS_SELECT_FILE)

        # No Settings Tab Events needed

        # === Processing Button Click ===
        if event == "-PROCESS-" and demucs_ok:
            filepath_str = values["-FILEPATH-"]
            if not filepath_str or not Path(filepath_str).is_file():
                gui.update_status(
                    window, "** Error: Please select a valid audio file first! **"
                )
                continue
            if PROCESSING_THREAD is not None and PROCESSING_THREAD.is_alive():
                sg.popup_error("Processing already in progress!", title="Busy")
                continue

            # Start the processing thread without passing settings
            gui.update_process_button(window, disabled=True)
            gui.update_status(window, "Starting processing thread...")
            PROCESSING_THREAD = threading.Thread(
                target=process_audio_thread,
                args=(filepath_str, window),  # Simpler args
                daemon=True,
            )
            PROCESSING_THREAD.start()

        # --- Thread Communication ---
        if event == "-THREAD_UPDATE-":
            gui.update_status(window, values[event])
        if event == "-REFRESH_SONGS-":
            # Refresh using default library path
            gui.update_song_list(window, file_manager.get_processed_songs())
        if event == "-THREAD_DONE-":
            gui.update_process_button(window, disabled=False)
            PROCESSING_THREAD = None

        # --- Song List Interaction ---
        if event == "-SONG_LIST-":
            if values["-SONG_LIST-"]:
                selected_song = values["-SONG_LIST-"][0]
                gui.update_status(window, f"Selected song: {selected_song}")

    # --- Cleanup ---
    window.close()


# --- Entry Point ---
if __name__ == "__main__":
    main()
