# Frontend Investigation Report

This report summarizes the findings from the analysis of the frontend codebase. The goal was to understand the current state of the application and determine the steps required to implement a robust testing strategy.

## 1. Tooling and Configuration

*   **Conclusion**: The project's tooling is modern, well-configured, and follows current best practices.
*   **Details**:
    *   The project uses React 19, Vite, pnpm, TypeScript, and Tailwind CSS.
    *   Build, linting (`eslint`), formatting (`prettier`), and type-checking (`tsc`) scripts are properly set up.
    *   The ESLint configuration uses the modern "flat config" format.
    *   Vite is correctly configured for proxying, PWA features, and path aliases.
*   **Assessment**: The foundation is solid. No issues were found in the project's setup or configuration.

## 2. Code Structure and Architecture

*   **Conclusion**: The codebase exhibits two competing architectural patterns: a modern, highly-testable hooks-based architecture, and an older, less-maintainable "container component" pattern.
*   **Details**:
    *   **The Good Pattern (`KaraokePlayer`)**: The `KaraokePlayer` component is a prime example of excellent architecture.
        *   **Hooks-based Logic**: All complex logic is extracted into custom hooks (`useKaraokePlayer`, `usePlayerUI`). This separates the "how" from the "what."
        *   **Decomposition**: The UI is broken into small, single-responsibility subcomponents.
        *   **Testability**: This structure is highly testable. The logic hooks can be unit-tested in isolation, and the UI components can be tested presentationally.
    *   **The Problematic Pattern (`Library.tsx`)**: The `Library` page represents the "hot mess."
        *   **Mixed Concerns**: The component is responsible for state management, data fetching, event handling, and rendering logic all in one file.
        *   **Difficult to Test**: Testing this component requires extensive mocking of hooks, child components, and navigation, indicating that the component is doing too much.
    *   **Overall Structure**: The `src` directory is organized by file type (e.g., `components`, `hooks`, `pages`). While common, this has led to feature-related code being scattered across the application.

## 3. State Management

*   **Conclusion**: The project uses a mix of tools for state management, which is appropriate. TanStack Query is used for server state, and Zustand is available for global client state. The issue is not the tools, but how they are used within components.
*   **Details**: In components like `Library.tsx`, data fetching logic is directly entangled with the component's rendering, which should be abstracted.

## Recommendations

The frontend is not in a "hot mess" state, but rather in a state of **architectural inconsistency**. A significant portion of the application (`KaraokePlayer`) demonstrates a clear path to a highly maintainable and testable codebase. The primary goal of the refactoring effort should be to apply this excellent pattern across the rest of the application.

### 1. Adopt the Hooks-Based Architecture Universally

*   **Action**: Refactor existing "container" components (like `Library.tsx`) to delegate all logic to custom hooks.
*   **Example (`Library.tsx` Refactor)**:
    1.  Create a `useLibraryManager` hook that encapsulates all state, data fetching (`useSongs`, `useArtists`), search logic, and event handlers.
    2.  The `LibraryPage` component should then become a simple, "dumb" component that calls `useLibraryManager` and passes the returned values to its child components.

### 2. Transition to a Feature-Based ("Slice") Directory Structure

*   **Action**: Gradually reorganize the `src` directory to group files by feature, not by type.
*   **Example (`Library` Feature)**:
    ```
    src/features/library/
    ├── components/
    │   ├── ArtistResultsSection.tsx
    │   ├── LibrarySearchInput.tsx
    │   └── SongResultsSection.tsx
    ├── hooks/
    │   └── useLibraryManager.ts
    ├── index.ts  // Exports the main LibraryPage component
    └── LibraryPage.tsx
    ```
    This co-locates all related files, making the feature easier to understand, maintain, and test.

### 3. Implement a Testing Strategy

Once the refactoring is underway, we can introduce a testing strategy.

*   **Tooling**: Use **Vitest** for running tests (as it integrates seamlessly with Vite) and **React Testing Library** for rendering components.
*   **What to Test**:
    1.  **Hooks (Unit Tests)**: The logic hooks (e.g., `useLibraryManager`, `useKaraokePlayer`) should be the primary focus of unit tests. Mock their dependencies (like API calls) and test their internal logic thoroughly.
    2.  **Components (Component/Integration Tests)**: Test the UI components by mocking the hooks they depend on. Verify that they render correctly based on the props and data they receive.
    3.  **User Flows (End-to-End Tests)**: Use a tool like Cypress or Playwright for end-to-end testing of critical user flows (e.g., searching for a song and playing it). This should be considered after the initial unit/integration test foundation is built.

## Next Steps

The next step is to begin **Phase 3: Initial Implementation & Proof of Concept**.

1.  **Refactor `Library.tsx`**: Apply the recommended changes to `Library.tsx` by creating a `useLibraryManager` hook.
2.  **Write Tests**: Create the first tests for the new `useLibraryManager` hook and the refactored `LibraryPage` component to establish a testing pattern.

This will serve as a concrete example for all future frontend development and refactoring efforts.