export interface RecentlyAddedSongsProps {
  limit?: number;
}

export interface PaginationState {
  currentPage: number;
  displayPage: number;
  isAnimating: boolean;
}

export interface PaginationActions {
  nextPage: () => void;
  reset: () => void;
}

export interface UsePaginationOptions {
  itemsPerPage: number;
  totalItems: number;
  animationDuration?: number;
}

export interface UsePaginationResult {
  state: PaginationState;
  actions: PaginationActions;
  hasNextPage: boolean;
  currentPageItems: <T>(items: T[]) => T[];
  nextPageItems: <T>(items: T[]) => T[];
}
