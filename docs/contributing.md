# Contributing

This project welcomes contributions! Here's how to get involved:

## Development Setup

1. Clone the repository
2. Install dependencies: `pnpm install` (installs all workspaces)
3. Start development with `./scripts/dev.sh` or `pnpm dev:frontend`

## Workspace Structure

This is a pnpm monorepo with workspaces:
- **frontend**: React 19 + TypeScript in `/frontend`
- **docs**: VitePress documentation in `/docs`
- **backend**: FastAPI in `/backend`

## Making Changes

- **Frontend**: Use TypeScript, follow ShadCN/UI patterns, use TanStack Query + Zustand
- **Backend**: Use FastAPI async endpoints, follow existing patterns
- **Docs**: Edit markdown files in `/docs`

## Running Commands

From root directory:
- `pnpm dev:frontend` - Start React dev server
- `pnpm dev:backend` - Start FastAPI server
- `pnpm docs:dev` - Start VitePress docs
- `pnpm build` - Build frontend
- `pnpm docs:build` - Build docs
- `pnpm test` - Run tests

## Code Quality

- **Frontend**: `pnpm lint:frontend`, `pnpm run check`
- **Backend**: `pnpm check:backend`

## Submitting Changes

1. Create a feature branch
2. Make your changes with clear commits
3. Ensure tests pass and linting is clean
4. Submit a pull request

For questions, check existing documentation or open an issue!
