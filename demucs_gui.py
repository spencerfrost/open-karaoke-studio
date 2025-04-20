import PySimpleGUI as sg
import threading
import time  # Only needed for demo if Demucs isn't run
from pathlib import Path
import sys
import traceback  # For more detailed error logging

# --- Try importing Demucs ---
# This checks if demucs is installed correctly before defining the layout
try:
    # Try importing the specific components needed
    from demucs.api import Separator, save_audio
    import torch

    demucs_available = True
    # Define standard stems (you might adjust if using models with different outputs)
    # The default 'htdemucs' and 'htdemucs_ft' provide these four.
    DEFAULT_STEMS = ["vocals", "drums", "bass", "other"]
except ImportError as e:
    print(f"Error importing Demucs or PyTorch: {e}", file=sys.stderr)
    print(
        "Please ensure Demucs and PyTorch are installed correctly in your venv.",
        file=sys.stderr,
    )
    print(
        "Try running: pip install git+https://github.com/adefossez/demucs",
        file=sys.stderr,
    )
    demucs_available = False
    DEFAULT_STEMS = []  # No stems available if import fails
except Exception as e:
    print(f"An unexpected error occurred during import: {e}", file=sys.stderr)
    traceback.print_exc()  # Print full traceback for unexpected errors
    demucs_available = False
    DEFAULT_STEMS = []


# --- Demucs Processing Function (to run in a thread) ---
def run_demucs_separation(filepath, selected_stems_to_save, window):
    """Runs Demucs separation in a separate thread and saves selected stems."""
    if not demucs_available:
        window.write_event_value(
            "-THREAD-", "** Demucs/PyTorch not installed correctly **"
        )
        return
    if not selected_stems_to_save:
        window.write_event_value("-THREAD-", "** Error: No stems selected to save! **")
        return

    try:
        if not filepath or not Path(filepath).is_file():
            raise ValueError("Invalid file path provided.")

        input_path = Path(filepath)
        # Create a subdirectory based on the input file name
        output_dir = input_path.parent / "separated" / input_path.stem
        output_dir.mkdir(parents=True, exist_ok=True)

        # --- Initialize Separator ---
        # Using default model 'htdemucs_ft' unless specified otherwise
        # Specify device (GPU if available, else CPU)
        device = "cuda" if torch.cuda.is_available() else "cpu"
        window.write_event_value("-THREAD-", f"Initializing Demucs (using {device})...")
        separator = Separator(
            model="htdemucs_ft", device=device
        )  # Default model - could be made selectable too!

        # --- Separate ---
        window.write_event_value(
            "-THREAD-", f"Loading and separating: {input_path.name}..."
        )
        # This separates all stems the model provides
        origin, separated = separator.separate_audio_file(str(input_path))
        # 'separated' is a dict: {'vocals': tensor, 'drums': tensor, ...}

        # --- Save Selected Stems ---
        window.write_event_value("-THREAD-", "Saving selected stems...")
        count = 0
        num_selected = len(selected_stems_to_save)
        for stem_name in selected_stems_to_save:
            if stem_name in separated:
                count += 1
                stem_wav = separated[stem_name]
                # Save as WAV by default, could add MP3 option later
                save_path = str(output_dir / f"{stem_name}.wav")
                window.write_event_value(
                    "-THREAD-", f"Saving {stem_name} ({count}/{num_selected})..."
                )
                # Save audio (tensor, path, samplerate)
                save_audio(stem_wav, save_path, separator.samplerate)
            else:
                # This might happen if the selected model doesn't produce a checked stem
                print(
                    f"Warning: Selected stem '{stem_name}' not found in model output.",
                    file=sys.stderr,
                )
                window.write_event_value(
                    "-THREAD-", f"** Warning: Stem {stem_name} not found **"
                )

        # --- Signal Completion ---
        window.write_event_value(
            "-THREAD-", f"Done! {count} stems saved in: {output_dir}"
        )

    except Exception as e:
        # Signal error
        print(f"Error during separation: {e}", file=sys.stderr)
        traceback.print_exc()  # Print full traceback to console for debugging
        window.write_event_value("-THREAD-", f"** Error: {e} **")


# === GUI Layout Definition ===

# Row 1: File Selection
file_browser_row = [
    sg.Text("Audio File:"),
    sg.Input(key="-FILEPATH-", readonly=True, enable_events=True),
    sg.FileBrowse(
        button_text="Browse",
        file_types=(
            ("Audio Files", "*.mp3 *.wav *.flac *.ogg *.m4a"),
            ("All Files", "*.*"),
        ),
    ),
]

# Row 2: Stem Selection Options
# Create checkboxes for the default stems
options_row = [sg.Text("Stems to save:")]
if demucs_available:
    options_row.extend(
        [
            sg.Checkbox(
                "Vocals", default=True, key="-vocals-"
            ),  # Default vocals to True
            sg.Checkbox("Drums", default=False, key="-drums-"),
            sg.Checkbox("Bass", default=False, key="-bass-"),
            sg.Checkbox("Other", default=False, key="-other-"),
            # Add more here if you use models like htdemucs_6s (guitar, piano)
        ]
    )
else:
    options_row.append(sg.Text("Stem selection disabled (Demucs not loaded)."))

# Row 3: Action Button and Status
action_row = [
    sg.Button(
        "Separate Selected Stems", key="-SEPARATE-", disabled=True
    ),  # Button to start
    sg.Text(
        "Status: Select an audio file", key="-STATUS-", size=(50, 1)
    ),  # Wider status
]

# Combine layout based on Demucs availability
if not demucs_available:
    layout = [
        [sg.Text("Demucs or PyTorch failed to import.")],
        [sg.Text("Please check console output and installation.")],
        [sg.Text(f"Attempted path: {sys.executable}")],  # Show python path being used
        [sg.Button("Exit")],
    ]
else:
    layout = [
        file_browser_row,
        [sg.HorizontalSeparator()],  # Add a visual separator
        options_row,
        [sg.HorizontalSeparator()],
        action_row,
    ]

# === Create Window ===
window_title = "Demucs Stem Separator GUI"
window = sg.Window(window_title, layout)

# === Event Loop ===
processing_thread = None

while True:
    event, values = window.read()

    if event == sg.WIN_CLOSED or event == "Exit":
        break

    # Enable/Disable Separate button based on file selection
    if event == "-FILEPATH-":
        filepath = values["-FILEPATH-"]
        if filepath and Path(filepath).is_file():
            window["-SEPARATE-"].update(disabled=False)
            window["-STATUS-"].update("Status: Ready to separate")
        else:
            window["-SEPARATE-"].update(disabled=True)
            window["-STATUS-"].update("Status: Select an audio file")

    # Start Separation Process
    if event == "-SEPARATE-":
        filepath = values["-FILEPATH-"]

        # Check if already processing
        if processing_thread is not None and processing_thread.is_alive():
            sg.popup_error("Separation already in progress!", title="Busy")
            continue  # Skip starting a new thread

        # Get selected stems from checkboxes
        selected_stems = []
        for stem in DEFAULT_STEMS:  # Iterate through known possible stems
            if values.get(f"-{stem}-", False):  # Check if the key exists and is True
                selected_stems.append(stem)

        # Validate file and selections
        if not filepath or not Path(filepath).is_file():
            window["-STATUS-"].update("** Error: Invalid or missing file path! **")
        elif not selected_stems:
            window["-STATUS-"].update(
                "** Error: Please select at least one stem to save! **"
            )
            sg.popup_error(
                "Please select at least one stem checkbox.", title="No Selection"
            )
        else:
            # --- Start the thread ---
            window["-SEPARATE-"].update(
                disabled=True
            )  # Disable button during processing
            window["-STATUS-"].update("Status: Starting...")
            processing_thread = threading.Thread(
                target=run_demucs_separation,
                # Pass the list of selected stems to the function
                args=(filepath, selected_stems, window),
                daemon=True,
            )
            processing_thread.start()

    # Handle status updates from the processing thread
    if event == "-THREAD-":
        status_message = values[event]
        window["-STATUS-"].update(f"Status: {status_message}")
        # Check if processing is finished (signalled by "Done!" or "** Error:")
        if status_message.startswith("Done!") or status_message.startswith("** Error:"):
            # Only re-enable if the button exists (i.e. demucs was available)
            if demucs_available:
                window["-SEPARATE-"].update(disabled=False)
            # Clear the thread variable, allowing a new run
            processing_thread = None


# --- Cleanup ---
window.close()
