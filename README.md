# Open Karaoke Studio

**(Project Status as of April 21, 2025: Initial development, core separation working, GUI basics in place.)**

A desktop application built with Python and Demucs to help create karaoke tracks by separating vocals from music. Includes a graphical interface for processing local audio files and managing a basic library.

The ultimate vision for this project is a fully-featured karaoke creation and playback experience, including YouTube integration and synchronized lyrics.

## Features

### Current Features:

* **Graphical User Interface (GUI):** Built with PySimpleGUI for ease of use.
* **Local File Processing:** Select local audio files (MP3, WAV, FLAC, etc.) via a file browser.
* **High-Quality Separation:** Utilizes state-of-the-art [Demucs models](https://github.com/adefossez/demucs) (specifically the `adefossez/demucs` fork) for audio source separation.
* **Karaoke Track Generation:** Automatically outputs separate `vocals` and `instrumental` tracks.
* **Format Matching:** Output files (`vocals`, `instrumental`) are saved in the same format as the input file (MP3 input -> MP3 output; WAV input -> WAV output; other formats default to WAV output).
* **Progress Indicator:** Real-time status updates in the GUI during the Demucs separation process.
* **Automatic Device Selection:** Uses GPU (CUDA) for processing if available and detected by PyTorch, otherwise falls back to CPU.
* **Song Library:**
    * Processed tracks are organized into a `karaoke_library` folder, with sub-folders for each song.
    * The original audio file is copied into the song's sub-folder for reference.
    * A basic listbox in the GUI displays the names of processed song folders found in the library.

### Planned Features / Vision:

* **Enhanced Settings:** A dedicated settings page/tab in the GUI to configure:
    * Processing device (Auto/CPU/GPU).
    * Choice of Demucs model.
    * Output quality parameters (MP3 bitrate, WAV bit depth).
    * Customizable library location.
* **YouTube Integration:**
    * Search YouTube for songs/videos directly within the application.
    * Download audio tracks from YouTube links using `yt-dlp`.
* **Improved Library Management:**
    * More robust scanning and display of processed songs.
    * Ability to add/edit metadata (artist, title, genre).
    * Search and filtering capabilities.
* **Karaoke Player:**
    * An integrated player window.
    * Playback of the generated instrumental track.
    * Loading and display of synchronized lyrics (e.g., from `.lrc` files).
    * Potential video playback capabilities.

## Requirements

* Python 3.8+
* PyTorch
* Torchaudio
* NumPy (`<2.0` - **Important:** Current PyTorch/Demucs builds often require NumPy 1.x series for compatibility)
* Demucs (`adefossez/demucs` fork from GitHub)
* PySimpleGUI

*(Future requirements will include `yt-dlp`, `Youtube-python` or similar)*

## Installation

1.  **Clone or Download:** Obtain the project files. If using Git:
    ```bash
    # Replace with your actual repository URL if you create one
    git clone [https://github.com/your_username/open-karaoke-studio.git](https://github.com/your_username/open-karaoke-studio.git)
    cd open-karaoke-studio
    ```
2.  **Create Virtual Environment:** It's highly recommended to use a virtual environment.
    ```bash
    python -m venv venv
    ```
3.  **Activate Virtual Environment:**
    * Windows: `.\venv\Scripts\activate`
    * macOS/Linux: `source venv/bin/activate`
4.  **Install Dependencies:** Install the required packages using pip. The order can sometimes matter, especially regarding NumPy compatibility.
    ```bash
    # Ensure NumPy < 2.0 is installed first for PyTorch compatibility
    pip install "numpy<2"

    # Install core PyTorch and Torchaudio (check PyTorch website for specific CUDA version commands if needed)
    pip install torch torchaudio

    # Install the GUI library
    pip install PySimpleGUI

    # Install Demucs directly from the adefossez fork on GitHub
    pip install git+[https://github.com/adefossez/demucs](https://github.com/adefossez/demucs)
    ```

## Usage

1.  Ensure your virtual environment is activated (`(venv)` should appear in your terminal prompt).
2.  Run the main application script from the project's root directory:
    ```bash
    python main.py
    ```
3.  The "Open Karaoke Studio" window will appear.
4.  Click "Browse" to select an audio file you want to process.
5.  Click the "Create Karaoke Tracks" button (it enables after a valid file is selected).
6.  Monitor the status bar at the bottom for progress updates (initialization, separation progress percentage, saving). Demucs separation can take time, especially on CPU.
7.  Upon completion, the status bar will indicate success or failure.
8.  Processed files (`vocals.*`, `instrumental.*`, and a copy of the original `*_original.*`) will be located in the `karaoke_library/YourSongName/` directory within the project folder.
9.  The "Processed Songs Library" listbox will update to show the folder name (`YourSongName`).

## Configuration

Currently, core processing settings are defined as constants in `config.py`:

* `DEFAULT_MODEL`: Specifies the Demucs model used (default: `htdemucs_ft`).
* `DEFAULT_MP3_BITRATE`: Sets the bitrate if the output format is MP3 (default: `320`).
* `BASE_LIBRARY_DIR`: The location where the `karaoke_library` folder is created (default: `./karaoke_library`).

*(A future update will introduce GUI settings saved to `settings.json`)*

## License

This project utilizes components (primarily Demucs) that are often distributed under the MIT license. Consider using the [MIT License](https://opensource.org/licenses/MIT) if you share this project.
