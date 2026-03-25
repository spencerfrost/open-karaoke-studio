# Library Loading State + Mobile Fixes Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix "No artists found" flash on page load by moving artist data fetching into `ArtistResultsSection`, and apply conservative mobile UX improvements.

**Architecture:** `ArtistResultsSection` becomes a smart component owning `useInfiniteArtists`, `useInfiniteScroll`, and the expandArtist side-effect — eliminating prop drilling and giving it direct access to `isLoading`. `ArtistAccordion` receives `isLoading` and shows a spinner instead of the empty state while data is in flight.

**Tech Stack:** React 19, TypeScript, TanStack Query v5, Tailwind CSS v4, Zustand

---

## Task 1: Refactor `ArtistResultsSection` into a smart component

**Files:**
- Modify: `frontend/src/features/library/components/ArtistResultsSection.tsx`

**Step 1: Replace the file contents**

```tsx
import React from "react";
import { useRef } from "react";
import { Users } from "lucide-react";
import ArtistAccordion from "./ArtistAccordion";
import { useInfiniteArtists } from "@/hooks/api/useInfiniteLibraryBrowsing";
import { useInfiniteScroll } from "@/hooks/useInfiniteScroll";

interface ArtistResultsSectionProps {
  searchTerm: string;
  expandArtist?: string | null;
}

const ArtistResultsSection: React.FC<ArtistResultsSectionProps> = ({
  searchTerm,
  expandArtist,
}) => {
  const effectiveSearchTerm = expandArtist ? "" : searchTerm;

  const {
    artists,
    hasNextPage,
    isFetchingNextPage,
    fetchNextPage,
    isLoading,
  } = useInfiniteArtists(effectiveSearchTerm, 200);

  const sentinelRef = useInfiniteScroll({
    loading: isFetchingNextPage,
    hasMore: hasNextPage,
    onLoadMore: fetchNextPage,
    threshold: 0.1,
    rootMargin: "100px",
  });

  // When expandArtist is set, keep fetching pages until the artist is found
  React.useEffect(() => {
    if (
      expandArtist &&
      !artists.find((a) => a.name === expandArtist) &&
      hasNextPage &&
      !isFetchingNextPage
    ) {
      fetchNextPage();
    }
  }, [expandArtist, artists, hasNextPage, isFetchingNextPage, fetchNextPage]);

  const sectionTitle = searchTerm.trim() ? "Artists" : "Browse All Artists";

  return (
    <div>
      <div className="flex items-center gap-3 mb-6">
        <Users size={24} className="text-orange-peel" />
        <h2 className="text-xl font-semibold text-orange-peel">
          {sectionTitle}
        </h2>
      </div>

      <ArtistAccordion
        artists={artists}
        isLoading={isLoading}
        hasNextPage={hasNextPage}
        isFetchingNextPage={isFetchingNextPage}
        fetchNextPage={fetchNextPage}
        sentinelRef={sentinelRef}
        expandArtist={expandArtist}
      />
    </div>
  );
};

export default ArtistResultsSection;
```

**Step 2: Type-check**

```bash
cd frontend && pnpm run check
```

Expected: Type errors on `ArtistAccordion` (it doesn't accept `isLoading` yet — fix in Task 2).

---

## Task 2: Add `isLoading` to `ArtistAccordion` + fix empty state

**Files:**
- Modify: `frontend/src/features/library/components/ArtistAccordion.tsx`

**Step 1: Add `isLoading` to the props interface**

In `ArtistAccordionProps` (around line 15), add:
```ts
isLoading?: boolean;
```

**Step 2: Add `isLoading` to the destructured props**

In the function signature, add `isLoading = false` to the destructured props.

**Step 3: Replace the empty-state check (lines 181–187)**

```tsx
// Before
if (!artists.length) {
  return (
    <div className={`text-center py-8 text-gray-500 ${className}`}>
      No artists found.
    </div>
  );
}

// After
if (isLoading && !artists.length) {
  return (
    <div className={`flex justify-center py-12 ${className}`}>
      <LoadingSpinner size={24} />
    </div>
  );
}

if (!artists.length) {
  return (
    <div className={`text-center py-8 text-gray-500 ${className}`}>
      No artists found.
    </div>
  );
}
```

Note: `LoadingSpinner` is already imported at the top of the file.

**Step 4: Type-check**

```bash
cd frontend && pnpm run check
```

Expected: No errors related to `ArtistAccordion`.

---

## Task 3: Simplify `Library.tsx` — remove artist data logic

**Files:**
- Modify: `frontend/src/pages/Library.tsx`

**Step 1: Remove unused imports**

Remove these import lines:
```ts
import { useInfiniteArtists } from "@/hooks/api/useInfiniteLibraryBrowsing";
import { useInfiniteScroll } from "@/hooks/useInfiniteScroll";
```

**Step 2: Remove the artist data block (roughly lines 47–62)**

Delete:
```ts
const {
  artists,
  hasNextPage,
  isFetchingNextPage,
  fetchNextPage,
  isLoading: artistsLoading,
} = useInfiniteArtists(effectiveSearchTerm, 200);

const sentinelRef = useInfiniteScroll({
  loading: isFetchingNextPage,
  hasMore: hasNextPage,
  onLoadMore: fetchNextPage,
  threshold: 0.1,
  rootMargin: "100px",
});
```

**Step 3: Remove the expandArtist fetch-until-found effect (lines 65–74)**

Delete:
```ts
React.useEffect(() => {
  if (
    expandArtist &&
    !artists.find((a) => a.name === expandArtist) &&
    hasNextPage &&
    !isFetchingNextPage
  ) {
    fetchNextPage();
  }
}, [expandArtist, artists, hasNextPage, isFetchingNextPage, fetchNextPage]);
```

**Step 4: Update `LibrarySearchInput` — remove `artistsLoading` from `isLoading` prop**

Change:
```tsx
isLoading={songsQuery.isLoading || artistsLoading}
```
To:
```tsx
isLoading={songsQuery.isLoading}
```

**Step 5: Update `ArtistResultsSection` usage — pass only 2 props**

Change:
```tsx
<ArtistResultsSection
  artists={artists}
  searchTerm={searchTerm}
  hasNextPage={hasNextPage}
  isFetchingNextPage={isFetchingNextPage}
  fetchNextPage={fetchNextPage}
  sentinelRef={sentinelRef}
  expandArtist={expandArtist}
/>
```
To:
```tsx
<ArtistResultsSection
  searchTerm={searchTerm}
  expandArtist={expandArtist}
/>
```

**Step 6: Fix mobile search bar margin**

Change the search bar wrapper div:
```tsx
// Before
<div className="my-12">

// After
<div className="my-4 sm:my-12">
```

**Step 7: Type-check**

```bash
cd frontend && pnpm run check
```

Expected: Clean.

**Step 8: Commit**

```bash
git add frontend/src/pages/Library.tsx \
        frontend/src/features/library/components/ArtistResultsSection.tsx \
        frontend/src/features/library/components/ArtistAccordion.tsx
git commit -m "fix: move artist data fetching into ArtistResultsSection, fix loading flash"
```

---

## Task 4: Fix `ArtistSection` — remove duplicate song count badge

**Files:**
- Modify: `frontend/src/features/library/components/ArtistSection.tsx`

**Step 1: Remove the orange pill badge**

Remove the following element from the artist header button (lines ~48–50):
```tsx
<div className="px-3 py-1 rounded-full text-sm font-medium bg-orange-peel text-dark-cyan">
  {songCount}
</div>
```

Song count is already shown in the paragraph: `{songCount} {songCount === 1 ? "song" : "songs"}`.

**Step 2: Fix broken Tailwind v4 utility**

On the `<button>` element, change:
```tsx
hover:bg-opacity-50
```
To:
```tsx
hover:bg-lemon-chiffon/5
```

(`hover:bg-opacity-50` is a Tailwind v3 modifier that has no effect in v4.)

**Step 3: Type-check and commit**

```bash
cd frontend && pnpm run check
git add frontend/src/features/library/components/ArtistSection.tsx
git commit -m "fix: remove duplicate song count badge, fix Tailwind v4 hover utility"
```

---

## Task 5: Fix `NavBar` iPhone safe-area padding

**Files:**
- Modify: `frontend/src/components/layout/NavBar.tsx`

**Step 1: Replace hardcoded bottom padding with safe-area-aware style**

On the `<nav>` element (line 25), change:
```tsx
// Before
<nav className="flex h-18 bg-russet border-t-1 border-border/80 sticky bottom-0 z-20 gap-4 pb-4 pt-2 md:py-1">

// After
<nav
  className="flex h-18 bg-russet border-t-1 border-border/80 sticky bottom-0 z-20 gap-4 pt-2 md:py-1"
  style={{ paddingBottom: 'calc(1rem + env(safe-area-inset-bottom))' }}
>
```

This ensures the nav bar content clears the home indicator on iPhones with notches. On non-notch devices `env(safe-area-inset-bottom)` resolves to `0px`, so the result is identical to the original `pb-4`.

**Step 2: Type-check and commit**

```bash
cd frontend && pnpm run check
git add frontend/src/components/layout/NavBar.tsx
git commit -m "fix: add safe-area-inset-bottom to NavBar for iPhone notch support"
```

---

## Task 6: Fix `RecentlyAddedSongs` — show spinner during load

**Files:**
- Modify: `frontend/src/features/library/components/RecentlyAddedSongs/RecentlyAddedSongs.tsx`

**Step 1: Add LoadingSpinner import**

```tsx
import LoadingSpinner from "@/components/ui/LoadingSpinner";
```

**Step 2: Replace the silent null return with a spinner**

```tsx
// Before
if (isLoading || songs.length === 0) {
  return null;
}

// After
if (isLoading) {
  return (
    <div className="flex justify-center py-12">
      <LoadingSpinner size={24} />
    </div>
  );
}

if (songs.length === 0) {
  return null;
}
```

**Step 3: Type-check and commit**

```bash
cd frontend && pnpm run check
git add frontend/src/features/library/components/RecentlyAddedSongs/RecentlyAddedSongs.tsx
git commit -m "fix: show loading spinner in RecentlyAddedSongs instead of blank"
```

---

## Verification Checklist

1. **Loading flash fixed:** Hard-refresh Library page → spinner appears while artists load → artists appear normally (no "No artists found" flash)
2. **Empty library:** If library has no songs, "No artists found" still appears correctly after load completes
3. **Search:** Type in search box → artists filter correctly, song results appear
4. **Artist expand:** Click an artist → songs load and display
5. **expandArtist URL param:** Navigate to `/?expandArtist=SomeArtist` → that artist expands automatically
6. **Mobile spacing:** At 375px viewport, search bar has less top/bottom margin than before
7. **Song count:** Expand an artist → song count shown only once (in the subtitle), no orange pill
8. **iPhone notch:** On device/simulator with home indicator, navbar content not cut off
9. **Recently Added loading:** Hard-refresh → spinner shows briefly instead of blank space
10. **Full check:** `cd frontend && pnpm run check` passes clean
