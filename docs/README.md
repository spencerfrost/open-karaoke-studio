# Documentation Deep-Dives

This directory contains detailed guides for complex topics that are too extensive for the main documentation files.

## Planned Topics

These documents can be created as needed when topics require deeper exploration:

### Technical Guides

**websocket-protocol.md**
- Complete WebSocket message protocol specification
- Message types, payloads, and flow diagrams
- Session lifecycle in detail
- Connection handling and error cases

**audio-processing.md**
- Deep-dive into audio separation engines
- Demucs vs Roformer comparison
- Processing pipeline internals
- GPU vs CPU performance analysis
- Adding new separation engines

**session-management.md**
- Session lifecycle diagrams
- Device type roles and permissions
- Session state synchronization
- Host disconnect behavior
- Multi-session isolation guarantees

### Developer Guides

**deployment.md**
- Production deployment guide
- Docker configuration
- Environment variables
- Database setup (PostgreSQL)
- SSL/HTTPS setup
- Reverse proxy configuration (nginx)

**contributing.md**
- Code contribution guidelines
- Development workflow
- Testing requirements
- PR process
- Code review checklist

**api-reference.md**
- Complete REST API documentation
- Request/response schemas
- Authentication (future)
- Rate limiting (future)
- Error codes

### Feature Deep-Dives

**lyrics-system.md**
- LRC format specification
- Lyrics fetching providers
- Timestamp synchronization
- Count-in detection algorithm
- Timing offset implementation

**queue-system.md**
- Queue data model
- Position management
- Reordering algorithm (when implemented)
- Session-specific queue isolation
- Queue state synchronization

**player-architecture.md**
- Web Audio API usage
- Dual-track playback implementation
- Volume/pitch/tempo control
- State management patterns
- Mini-player design

## Current Status

Currently, all documentation resides in the top-level markdown files:

- [FEATURES.md](../FEATURES.md) - Feature inventory
- [ARCHITECTURE.md](../ARCHITECTURE.md) - System architecture
- [TECH-DEBT.md](../TECH-DEBT.md) - Known issues
- [ROADMAP.md](../ROADMAP.md) - Future plans
- [CLAUDE.md](../CLAUDE.md) - AI assistant context

Create documents in this directory when:
- A topic becomes too detailed for the main docs
- You need diagrams and visual explanations
- Implementation details need extensive documentation
- You want to preserve architectural decision records (ADRs)

## Document Template

When creating a new document:

1. Start with an overview
2. Include diagrams where helpful (use ASCII art or links to images)
3. Add code examples
4. Link back to relevant main documentation
5. Keep the audience in mind (solo dev, not team onboarding)

## Maintenance

These documents should be:
- **Pragmatic** - Focus on what's needed, not exhaustive
- **Up-to-date** - Update when architecture changes
- **Linked** - Cross-reference with main docs
- **Searchable** - Use clear headers and keywords
