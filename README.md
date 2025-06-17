# 🎶 Open Karaoke Studio 🎤

**Your open-source AI powered karaoke studio!**

Open Karaoke Studio is a web application designed to make it easy for you to generate instrumental versions of your favorite songs. By using AI-powered vocal separation, it provides the tools to create custom karaoke tracks.

## Current Features

- 💿 **Upload & Process:** Upload your favorite songs and let the AI do the rest.
- ✂️ **Vocal Separation:** Cleanly extract vocals from any song.
- 🎸 **Create Instrumentals:** Get high-quality instrumental tracks for your karaoke sessions.
- 📂 **Song Library:** Keep track of your processed songs in a user-friendly library.
- 🚀 **Modern & Fast:** Built with cutting-edge web technologies for a smooth experience.
- 🖥️ **Web Interface:** A sleek, user-friendly interface for a seamless experience.
- 🔍 **Song Search:** Search for songs from Youtube and automatically generate karaoke tracks.
- 🔄 **Asynchronous Processing:** Queue up multiple song processing jobs to run in the background
- 🛜 **Self-hosting:** Self-host your own personal karaoke library and player

## New: Lyric Timing Solutions 🎯

- 🔧 **Logic-First Alignment:** Automatically detect and fix timing misalignment between vocals and synced lyrics
- 🤖 **AI-Generated Lyrics:** Use speech recognition to create perfectly timed lyrics from audio (experimental)
- 📊 **Batch Analysis:** Test timing alignment across your entire music library
- ⚡ **Quick Fixes:** Get specific correction values to fix karaoke timing issues

👉 **[Learn more about Lyric Timing Solutions](./docs/LYRIC_TIMING_SOLUTIONS.md)**

## Planned Features

- ⚙️ **Settings/Configuration:** Customize your experience and song processing options.
- 📺 **Karaoke Player:** Integrated karaoke player for seamless playbook.
- 🎙️ **Vocal Guide:** Adjust the volume of the original vocals to sing along.
- 🩺 **Beat Detection:** Automatic beat synchronization for lyrics display
- 🤖 **Lyrics Display:** Auto-generate karaoke-style lyrics graphics
- 📱 **Mobile Support:** Add songs from your mobile device and enjoy on-the-go functionality.
- 🎚️ **Audio Effects:** Apply real-time effects to vocals and instrumentals

## Tech Stack

Open Karaoke Studio uses modern web technologies for performance and maintainability:

- **Frontend:** React 19 + TypeScript, Vite, Tailwind CSS, Shadcn/UI
- **Backend:** Python + Flask, Demucs AI, SQLAlchemy, Celery + Redis
- **Architecture:** Simplified shared repository with independent frontend and backend services

**📋 Detailed Information:**

- **[Architecture Overview](./docs/architecture/README.md)** - Complete system design
- **[Frontend Details](./frontend/README.md)** - React application structure
- **[Backend Details](./docs/architecture/backend/README.md)** - Python API and services

## Getting Started

**New to Open Karaoke Studio?** Follow our comprehensive setup guide:

👉 **[Complete Installation Guide](./docs/getting-started/installation.md)** - Everything you need to get started

### Quick Start

1. **Clone the Repository** - Get the project code
2. **Install Dependencies** - Python, Node.js, and packages
3. **Run One Command** - `./scripts/dev.sh` (starts everything!)
4. **Process Your First Song** - [Follow the tutorial](./docs/getting-started/first-song.md)

**Time needed:** ~10 minutes to be up and running

**Perfect for karaoke parties** - Other devices can connect via your network IP!

### More Resources

- **[📚 Complete Documentation](./docs/README.md)** - Full documentation hub
- **[🎵 User Guide](./docs/user-guide/README.md)** - Learn all features
- **[🔧 Troubleshooting](./docs/getting-started/troubleshooting.md)** - Common issues and solutions
- **[👩‍💻 Development Guide](./docs/development/README.md)** - For contributors

## Contributing

We welcome contributions to Open Karaoke Studio! If you're interested in contributing, please:

1.  Fork the repository.
2.  Create a branch for your changes.
3.  Implement your feature or bug fix.
4.  Submit a pull request.

## License

This project is licensed under the MIT License. See the [LICENSE](./LICENSE) file for details.
