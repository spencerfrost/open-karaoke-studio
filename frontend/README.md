# Open Karaoke Studio - Frontend

This document provides information about the frontend component of the Open Karaoke Studio application.

## Table of Contents

* [Project Description](#project-description)
* [Technologies](#technologies)
* [Directory Structure](#directory-structure)
* [Getting Started](#getting-started)
    * [Prerequisites](#prerequisites)
    * [Installation](#installation)
    * [Development](#development)
* [Components](#components)
* [Hooks](#hooks)
* [Styling](#styling)
* [API Communication](#api-communication)
* [State Management](#state-management)
* [Build](#build)
* [Contributing](#contributing)
* [License](#license)

## Project Description

The frontend of Open Karaoke Studio is a React application built with TypeScript. It provides the user interface for interacting with the backend API to upload audio files, initiate audio processing, view the song library, and download separated audio tracks.

## Technologies

* React 19 with TypeScript
* Tailwind CSS
* Shadcn/UI
* TanStack Query
* Vite
* pnpm

## Getting Started

### Prerequisites

* Node.js
* pnpm

### Installation

1.  Navigate to the `frontend/` directory:

    ```bash
    cd frontend
    ```

2.  Install dependencies:

    ```bash
    pnpm install
    ```

### Development

1.  Start the development server:

    ```bash
    pnpm run dev
    ```

2.  The application will be served at a local URL (usually `http://localhost:5173`).

## Components

* **`ActionStatus.tsx`:**
    * Handles the "Create Karaoke Tracks" button and displays processing status.
    * Uses `useApiMutation` to trigger the audio processing API call.
    * Manages UI state related to processing status.
* **`FileBrowser.tsx`:**
    * Provides a file input for selecting audio files.
    * Displays the selected file path.
    * Manages the selected file data.
* **`SongLibrary.tsx`:**
    * Displays a list of processed songs retrieved from the API.
    * Uses `useApiQuery` to fetch the song data.
    * Presents song information in a table format.
* **`ui/`:**
    * Contains reusable UI components styled with Tailwind CSS and Shadcn/UI (e.g., buttons, inputs, tables, tabs).
    * These should be used throughout the application for consistent styling.
* **`ProcessLibraryTab.tsx`:**
    * Combines the `FileBrowser`, `ActionStatus`, and `SongLibrary` components to create the main processing and library interface.
    * Manages the state of the selected file and passes it to `ActionStatus`.

## Hooks

* **`useApiData.ts`:**
    * A custom hook that encapsulates API communication logic.
    * Provides `useApiQuery` for `GET` requests and `useApiMutation` for `POST`, `PUT`, `PATCH`, and `DELETE` requests.
    * Handles data fetching, caching, and error handling using TanStack Query.
    * Includes a separate `uploadFile` function for file uploads.

## Styling

* Tailwind CSS is used for utility-first styling.
* Shadcn/UI provides pre-built, accessible UI components styled with Tailwind CSS.

## API Communication

* The frontend communicates with the backend API using `fetch` (for general requests and file uploads) and TanStack Query (for managing queries and mutations).
* API endpoints:
    * `/process` (POST):  Uploads an audio file and initiates processing.
    * `/status/{filename}` (GET):  Gets the processing status of a file.
    * `/songs` (GET):  Retrieves a list of processed songs.
    * `/download/{filename}` (GET):  Downloads a processed audio file.

## State Management

* TanStack Query manages server state (data fetched from the API).
* React's `useState` is used for local component state.
* Zustand may be used for more complex global application state (if needed).

## Build

* Vite is used to build the frontend for production:

    ```bash
    pnpm run build
    ```

* The built assets will be located in the `dist/` directory.

## Contributing

Contributions are welcome! Please follow these steps:

1.  Fork the repository.
2.  Create a new branch for your feature or bug fix.
3.  Make your changes and commit them.
4.  Push your changes to your fork.
5.  Submit a pull request.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.