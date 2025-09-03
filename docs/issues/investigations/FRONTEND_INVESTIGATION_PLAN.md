# Frontend Investigation & Refactoring Plan

This document outlines a phased approach to investigate the current state of the Open Karaoke Studio frontend, identify key problem areas, and establish a roadmap for refactoring that will enable a robust testing strategy.

### Phase 1: Discovery & Codebase Analysis

The goal of this phase is to gain a deep understanding of the existing frontend architecture, patterns, and pain points.

1.  **Tooling and Configuration Review:**
    *   Analyze `vite.config.ts`, `tsconfig.json`, `eslint.config.js`, and `package.json`.
    *   **Objective:** Verify that the build process, type checking, and linting are configured correctly and using modern standards.

2.  **Code Structure and Organization:**
    *   Map the current directory structure within `frontend/src`.
    *   **Objective:** Identify the architectural patterns (or lack thereof). Determine if the structure is based on features, components, or another convention.

3.  **Component Analysis:**
    *   Identify the largest and most complex components.
    *   Analyze component responsibilities: Are components mixing concerns (e.g., UI, state management, data fetching)?
    *   **Objective:** Pinpoint major candidates for refactoring into smaller, single-responsibility components.

4.  **State Management Strategy:**
    *   Investigate the use of `useState`, `useContext`, and other React hooks for state.
    *   Analyze the implementation of TanStack Query for server state.
    *   **Objective:** Determine if state management is consistent and efficient, or if it's leading to prop-drilling and complex component coupling.

5.  **Styling and UI Components:**
    *   Review the usage of Tailwind CSS and Shadcn/UI.
    *   **Objective:** Check for consistency in styling and component usage. Identify any large-scale CSS overrides or non-standard implementations.

### Phase 2: Synthesis & Recommendations

Based on the findings from Phase 1, this phase will produce a clear report and a set of actionable recommendations.

1.  **Create `FRONTEND_INVESTIGATION_REPORT.md`:**
    *   This report will summarize the findings from the analysis, detailing the current state of the codebase with specific examples.

2.  **Define a Target Architecture:**
    *   Propose a clear, modern React architecture to strive for (e.g., feature-based directories, clear separation of concerns, defined component types).

3.  **Develop a Refactoring Roadmap:**
    *   Create a prioritized list of refactoring tasks. This will likely involve breaking down large components, creating reusable hooks, and standardizing data fetching and state management.

4.  **Propose a Testing Strategy:**
    *   Recommend a testing framework (e.g., Vitest, React Testing Library).
    *   Define what to test and how:
        *   **Unit Tests:** For hooks and utility functions.
        *   **Component Tests:** For individual UI components in isolation.
        *   **Integration Tests:** For user flows that involve multiple components.

### Phase 3: Initial Implementation & Proof of Concept

To validate the proposed plan, we will execute a small, focused refactoring and testing effort.

1.  **Select a Pilot Component:**
    *   Choose one moderately complex but non-critical component from the analysis.

2.  **Refactor and Test:**
    *   Refactor the chosen component according to the new architectural guidelines.
    *   Implement unit and/or component tests, establishing a testing pattern for future development.

3.  **Document the Process:**
    *   Create a guide for developers on how to follow the new patterns and write tests.