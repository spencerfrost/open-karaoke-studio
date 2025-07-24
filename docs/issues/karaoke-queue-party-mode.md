# Karaoke Queue System Design (Party Mode)

## Overview
This document outlines the design and requirements for a new, robust karaoke queue system for "party mode" in Open Karaoke Studio. The goal is to create a simple, extensible, and real-time queue experience for multiple users/devices sharing the same app instance.

* Note: the current implementation is placeholder content and does not need to be maintained for backwards compatibility. *

## Components
- **Stage**: The main party mode interface, where the karaoke queue is displayed and managed.
- **KaraokeQueueList**: 
- **KaraokeQueueItem** 
- **UnifiedLyricsDisplay**

## Key Behaviors
- The karaoke queue is only present in party mode. Solo mode does not display or use a queue.
- Anyone can interact with the queue (add, play, remove songs). Authorization and permissions will be added later.
- The queue component displays the list of queued songs, with action buttons for each item:
  - **Play**: Moves the song from the queue into the player.
  - **Remove**: Removes the song from the queue.
- Adding songs to the queue is done from the library page, not from the queue component itself.
- When a song finishes, the next song in the queue can be played manually (via the Play button). Auto-play may be considered later.

## User Stories & Flows
- As a user, I can add songs to the queue from the library page.
- As a user, I can see the current queue and what’s playing.
- As a user, I can remove any song from the queue.
- As a user, I can play any song in the queue (moves it to the player).
- As a user, I see real-time updates when the queue changes.

## Data Model
Each queue entry should include:
- Song ID
- Title
- Artist
- Who added it (optional for now)
- Status (e.g., queued, playing, played)
- Order (to track queue position)

## Storage & Real-Time Updates
- The queue will be stored in the database (table: `karaoke_queue`).
- Real-time updates will be handled via WebSocket (or similar) so all clients see changes instantly.

## API & WebSocket
- REST endpoints for queue actions: add, remove, list, play.
- WebSocket channel for real-time queue updates.

## Concurrency & Consistency
- The backend must handle simultaneous actions (e.g., two users adding at once) gracefully.
- Each queue entry should have a unique order/index. The database should enforce order and atomicity.
- If two users add at the same time, both songs should be added, and the order should be consistent (e.g., by timestamp or auto-incremented index).

## Permissions & Validation
- For now, no restrictions: anyone can add, play, or remove any song.
- Validation is minimal, as song data comes directly from the library UI.

## UI/UX Considerations
- The queue is displayed as a card with list items, each with Play and Remove buttons.
- Adding to the queue is done from the library page.
- Errors are communicated via toast notifications.

## Testing & Robustness
- Plan for basic unit and integration tests.
- Consider edge cases: empty queue, duplicate songs, disconnects.

## Extensibility
- The system should be designed to allow for future features: permissions, reordering, voting, lobbies, etc.

---

This document serves as the foundation for implementing the new karaoke queue system. Further technical details and implementation plans can be added as the design evolves.
