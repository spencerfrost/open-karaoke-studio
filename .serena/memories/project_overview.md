# Open Karaoke Studio - Project Overview

## Purpose
Open Karaoke Studio is an open-source AI-powered karaoke studio web application that makes it easy to generate instrumental versions of your favorite songs using AI-powered vocal separation.

## Key Features
- **Upload & Process**: Upload songs and let AI create instrumental tracks
- **Vocal Separation**: Cleanly extract vocals from any song using Demucs AI
- **Song Library**: User-friendly library management system
- **YouTube Integration**: Search for songs from YouTube and automatically generate karaoke tracks
- **Asynchronous Processing**: Queue multiple song processing jobs in the background
- **Lyric Timing Solutions**: AI-generated lyrics with timing alignment
- **Self-hosting**: Personal karaoke library and player
- **Modern Web Interface**: Sleek, responsive UI

## Architecture
- **Shared Repository**: Independent frontend and backend services
- **AI Processing**: Uses Demucs for vocal separation and Whisper for lyrics generation
- **Real-time Updates**: WebSocket integration for job status updates
- **Background Processing**: Celery with Redis for heavy audio processing tasks

## Target Users
- Karaoke enthusiasts who want to create custom tracks
- Musicians and content creators
- Self-hosting enthusiasts
- Party hosts who want a personal karaoke system