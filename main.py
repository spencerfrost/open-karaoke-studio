# main.py
"""Main application file for Open Karaoke Studio."""

import PySimpleGUI as sg
import threading
import sys
import traceback
from pathlib import Path

# Import our modules
import config
import gui
import demucs_processor
import file_manager

# --- Global variable for the processing thread ---
processing_thread = None


def process_audio_thread(filepath_str, window):
    """Target function for the audio processing thread."""
    global processing_thread  # Allow modification of the global variable

    def gui_callback(message):
        """Function to send status updates back to the main thread."""
        if window:
            window.write_event_value("-THREAD_UPDATE-", message)

    try:
        filepath = Path(filepath_str)
        gui_callback(f"Starting processing for {filepath.name}...")

        # 1. Ensure library and create song directory
        file_manager.ensure_library_exists()
        song_dir = file_manager.get_song_dir(filepath)
        gui_callback(f"Created song directory: {song_dir}")

        # 2. Copy original file
        gui_callback("Copying original file...")
        original_saved_path = file_manager.save_original_file(filepath, song_dir)
        if not original_saved_path:
            gui_callback("** Error: Failed to copy original file. Aborting. **")
            return  # Stop processing if copy fails

        # 3. Separate audio
        success = demucs_processor.separate_audio(filepath, song_dir, gui_callback)

        # 4. Final status update
        if success:
            gui_callback(f"Successfully processed {filepath.name}!")
            # Trigger song list refresh in main thread
            window.write_event_value("-REFRESH_SONGS-", None)
        else:
            gui_callback(f"Processing failed for {filepath.name}.")

    except Exception as e:
        print(f"Critical error in processing thread: {e}", file=sys.stderr)
        traceback.print_exc()
        gui_callback(f"** Critical Thread Error: {e} **")
    finally:
        # Signal thread completion (runs whether success or failure)
        if window:
            window.write_event_value("-THREAD_DONE-", None)


def main():
    """Main application function."""
    global processing_thread

    # Initial checks
    demucs_ok = demucs_processor.is_available()

    # Create the main window
    window = gui.create_main_window(demucs_ok)

    # Load initial song list if Demucs is okay
    if demucs_ok:
        gui.update_song_list(window, file_manager.get_processed_songs())

    # --- Event Loop ---
    while True:
        event, values = window.read()

        if event == sg.WIN_CLOSED or event == "Exit":
            # Check if thread is running before closing
            if processing_thread is not None and processing_thread.is_alive():
                # Maybe add a prompt here asking the user if they're sure
                print("Warning: Closing window while processing is active.")
            break

        # --- GUI Event Handling ---

        # File selected -> Enable button
        if event == "-FILEPATH-" and demucs_ok:
            filepath = values["-FILEPATH-"]
            if filepath and Path(filepath).is_file():
                gui.update_process_button(window, disabled=False)
                gui.update_status(window, "Ready to process")
            else:
                gui.update_process_button(window, disabled=True)
                gui.update_status(window, config.DEFAULT_STATUS_SELECT_FILE)

        # Process button clicked
        if event == "-PROCESS-" and demucs_ok:
            filepath_str = values["-FILEPATH-"]

            # Basic validation
            if not filepath_str or not Path(filepath_str).is_file():
                gui.update_status(
                    window, "** Error: Please select a valid audio file first! **"
                )
                continue

            # Check if already processing
            if processing_thread is not None and processing_thread.is_alive():
                sg.popup_error("Processing already in progress!", title="Busy")
                continue

            # Start the processing thread
            gui.update_process_button(window, disabled=True)  # Disable button
            gui.update_status(window, "Starting processing thread...")
            processing_thread = threading.Thread(
                target=process_audio_thread,
                args=(filepath_str, window),
                daemon=True,  # Allows main program to exit even if thread is running
            )
            processing_thread.start()

        # --- Thread Communication Handling ---

        # Update status text from thread
        if event == "-THREAD_UPDATE-":
            status_message = values[event]
            gui.update_status(window, status_message)

        # Refresh song list triggered by thread
        if event == "-REFRESH_SONGS-":
            gui.update_song_list(window, file_manager.get_processed_songs())

        # Re-enable button when thread is finished
        if event == "-THREAD_DONE-":
            gui.update_process_button(window, disabled=False)  # Re-enable button
            processing_thread = None  # Clear the thread variable
            # Keep the last status message from the thread

        # --- Future: Song List Interaction ---
        if event == "-SONG_LIST-":
            if values["-SONG_LIST-"]:  # Check if selection is not empty
                selected_song = values["-SONG_LIST-"][0]
                gui.update_status(window, f"Selected song: {selected_song}")
                # Add actions here later (e.g., enable a Play button)

    # --- Cleanup ---
    window.close()

# --- Application Entry Point ---
if __name__ == "__main__":
    main()
