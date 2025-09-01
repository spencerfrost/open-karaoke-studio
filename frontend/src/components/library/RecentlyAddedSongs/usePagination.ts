import { useState, useCallback, useMemo } from "react";
import { 
  PaginationState, 
  PaginationActions, 
  UsePaginationOptions, 
  UsePaginationResult 
} from "./RecentlyAddedSongs.types";

export const usePagination = ({
  itemsPerPage,
  totalItems,
  animationDuration = 300,
}: UsePaginationOptions): UsePaginationResult => {
  const [state, setState] = useState<PaginationState>({
    currentPage: 0,
    displayPage: 0,
    isAnimating: false,
  });

  const hasNextPage = useMemo(() => {
    return state.currentPage * itemsPerPage + itemsPerPage < totalItems;
  }, [state.currentPage, itemsPerPage, totalItems]);

  const nextPage = useCallback(() => {
    if (hasNextPage && !state.isAnimating) {
      setState(prev => ({ ...prev, isAnimating: true }));

      setTimeout(() => {
        setState(prev => ({
          currentPage: prev.currentPage + 1,
          displayPage: prev.displayPage + 1,
          isAnimating: false,
        }));
      }, animationDuration);
    }
  }, [hasNextPage, state.isAnimating, animationDuration]);

  const reset = useCallback(() => {
    setState({
      currentPage: 0,
      displayPage: 0,
      isAnimating: false,
    });
  }, []);

  const currentPageItems = useCallback(
    <T,>(items: T[]) => {
      const startIndex = state.displayPage * itemsPerPage;
      return items.slice(startIndex, startIndex + itemsPerPage);
    },
    [state.displayPage, itemsPerPage]
  );

  const nextPageItems = useCallback(
    <T,>(items: T[]) => {
      const nextStartIndex = (state.displayPage + 1) * itemsPerPage;
      return items.slice(nextStartIndex, nextStartIndex + itemsPerPage);
    },
    [state.displayPage, itemsPerPage]
  );

  const actions: PaginationActions = useMemo(
    () => ({ nextPage, reset }),
    [nextPage, reset]
  );

  return {
    state,
    actions,
    hasNextPage,
    currentPageItems,
    nextPageItems,
  };
};