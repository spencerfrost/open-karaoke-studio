# Component Refactoring Guide: Identifying and Fixing Common Issues

## Overview

This guide outlines common component architecture and code quality issues that degrade maintainability, testability, and developer experience. These patterns were identified during the SongCard component refactor and should be applied when reviewing other components in the codebase.

## 🚨 Critical Issues to Look For

### 1. God Components (Massive Single Components)

**What to look for:**
- Components over 200-300 lines of code
- Single files containing multiple sub-components
- Components handling multiple unrelated responsibilities
- Components with 10+ props or state variables

**Why it's problematic:**
- Hard to test individual pieces
- Difficult to reuse sub-components
- Changes in one area affect unrelated functionality
- Poor separation of concerns
- Overwhelming for new developers

**How to fix:**
- Split into focused sub-components
- Extract business logic to custom hooks
- Create clear component composition
- Use proper directory structure

**Example structure:**
```
components/
  MyComponent/
    index.ts                 # Clean exports
    MyComponent.tsx          # Main orchestrator
    MyComponent.types.ts     # Type definitions
    SubComponentA.tsx        # Focused sub-component
    SubComponentB.tsx        # Another focused sub-component
    MyComponent.hooks.ts     # Component-specific logic
```

### 2. Confusing Props Interfaces

**What to look for:**
- Multiple props that do the same thing (`onSelect` vs `onSongSelect`)
- Props with names like "for backward compatibility"
- Optional props that should be required
- Props that take `any` type
- Boolean props that could be enums/unions

**Why it's problematic:**
- Unclear API for consumers
- Maintenance burden
- Runtime errors from incorrect usage
- Poor TypeScript IntelliSense

**How to fix:**
- Consolidate duplicate props
- Use descriptive, unambiguous names
- Prefer union types over booleans where appropriate
- Remove "backward compatibility" cruft

**Before:**
```typescript
interface BadProps {
  onSelect?: (item: any) => void;
  onItemSelect?: (item: any) => void; // backward compatibility
  variant?: "grid" | "horizontal" | string;
  showActions?: boolean;
  showDelete?: boolean;
}
```

**After:**
```typescript
interface GoodProps {
  onItemClick: (item: Item) => void;
  variant: "compact" | "detailed";
  actions: Array<"delete" | "edit" | "share">;
}
```

### 3. Mixed Responsibilities in Components

**What to look for:**
- Components that handle:
  - Rendering UI
  - Managing state
  - Making API calls
  - Navigation logic
  - Business logic calculations
  - Form validation

**Why it's problematic:**
- Violates Single Responsibility Principle
- Hard to test business logic separately
- Coupling between UI and business concerns
- Difficult to reuse logic elsewhere

**How to fix:**
- Extract custom hooks for business logic
- Create service layers for API calls
- Use context for shared state
- Separate pure functions for calculations

### 4. Poor State Management

**What to look for:**
- Multiple related `useState` calls
- Complex state objects managed with `useState`
- State that could be derived from other state
- Missing state machines for complex flows

**Why it's problematic:**
- Potential for inconsistent state
- Hard to track state changes
- Race conditions
- Poor developer experience

**How to fix:**
- Use `useReducer` for complex state
- Create custom hooks for related state
- Implement state machines for complex flows
- Derive state where possible

**Before:**
```typescript
const [isDialogOpen, setIsDialogOpen] = useState(false);
const [isSingerDialogOpen, setIsSingerDialogOpen] = useState(false);
const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);
```

**After:**
```typescript
const dialogs = useSongDialogs(); // Unified state management
```

### 5. Inconsistent Component Structure

**What to look for:**
- Mix of components in single files vs separate files
- Inconsistent naming conventions
- Components defined inside other components
- Unclear component hierarchy

**Why it's problematic:**
- Inconsistent codebase patterns
- Hard to find specific components
- Poor code organization
- Confusing for new developers

**How to fix:**
- Establish consistent file/folder structure
- Use clear naming conventions
- Extract inline components to separate files
- Create component composition guidelines

### 6. Embedded Business Logic in UI Components

**What to look for:**
- Complex calculations in render methods
- API calls directly in components
- Business rules scattered throughout UI code
- Form validation logic in components

**Why it's problematic:**
- Hard to test business logic
- Coupling between UI and business concerns
- Difficult to change business rules
- Poor separation of concerns

**How to fix:**
- Extract to custom hooks
- Create service layers
- Use pure functions for calculations
- Implement proper validation libraries

### 7. Poor Action/Event Handling

**What to look for:**
- Inline event handlers with complex logic
- Actions that are always rendered but conditionally shown
- Inconsistent event handling patterns
- Missing event.stopPropagation() calls

**Why it's problematic:**
- Event bubbling issues
- Unnecessary rendering
- Inconsistent UX
- Hard to manage action availability

**How to fix:**
- Make actions declarative
- Use consistent event handling patterns
- Proper event management
- Clear action availability logic

**Before:**
```typescript
<ActionButtons
  onDelete={someCondition ? handleDelete : undefined}
  onEdit={anotherCondition ? handleEdit : undefined}
/>
```

**After:**
```typescript
<ActionButtons
  actions={getAvailableActions(item, permissions)}
  onAction={handleAction}
/>
```

## 🎯 Refactoring Strategy

### Phase 1: Assessment
1. Identify components over 200 lines
2. Look for multiple responsibilities
3. Check for confusing prop interfaces
4. Identify poor state management

### Phase 2: Planning
1. Define clear component boundaries
2. Plan custom hook extractions
3. Design new prop interfaces
4. Create component composition strategy

### Phase 3: Implementation
1. Extract custom hooks first
2. Split components by responsibility
3. Update prop interfaces
4. Create proper file structure
5. Update imports and exports

### Phase 4: Validation
1. Run type checking
2. Test functionality
3. Verify performance
4. Update documentation

## 🏗️ Best Practices for New Components

### Component Design
- **Single Responsibility**: One clear purpose per component
- **Composition over Configuration**: Prefer composing components over complex props
- **Declarative APIs**: Make component behavior clear from props
- **Type Safety**: Comprehensive TypeScript interfaces

### File Organization
```
components/
  ComponentName/
    index.ts                 # Clean exports
    ComponentName.tsx        # Main component
    ComponentName.types.ts   # Type definitions
    ComponentName.test.tsx   # Tests
    subcomponents/           # Sub-components if needed
    hooks/                   # Component-specific hooks
```

### Custom Hooks
- Extract business logic from components
- Create reusable state management
- Handle side effects properly
- Provide clear return interfaces

### State Management
- Use `useState` for simple local state
- Use `useReducer` for complex state objects
- Create custom hooks for related state
- Consider state machines for complex flows

## 🔍 Code Review Checklist

When reviewing components, ask:

- [ ] Does this component have a single, clear responsibility?
- [ ] Are the props interface clean and unambiguous?
- [ ] Is business logic extracted to hooks or services?
- [ ] Is the component easy to test?
- [ ] Is the file structure consistent with project patterns?
- [ ] Are there any "god component" anti-patterns?
- [ ] Is state management appropriate for the complexity?
- [ ] Are actions and events handled consistently?

## 📚 Examples of Good Component Architecture

The refactored `SongCard` component demonstrates these principles:

- **Clear separation**: UI components, business logic hooks, type definitions
- **Single responsibility**: Each sub-component has one purpose
- **Composable**: Components can be reused and customized
- **Type safe**: Clean interfaces with no ambiguity
- **Testable**: Logic extracted to hooks that can be tested independently

## 🚀 Impact of Good Component Architecture

- **Maintainability**: Easy to find and modify code
- **Testability**: Business logic can be tested separately
- **Reusability**: Components can be composed in different ways
- **Developer Experience**: Clear structure and interfaces
- **Performance**: Better separation reduces unnecessary re-renders
- **Scalability**: Easy to add new features without breaking existing functionality

---

*This guide should be consulted when reviewing existing components and designing new ones. Following these patterns will lead to a more maintainable and developer-friendly codebase.*