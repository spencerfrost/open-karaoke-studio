import { useState, useCallback, useMemo } from "react";

interface UsePaginationOptions {
  itemsPerPage: number;
  totalItems: number;
  initialPage?: number;
  onPageChange?: (page: number) => void;
}

interface PaginationInfo {
  currentPage: number;
  totalPages: number;
  hasNextPage: boolean;
  hasPreviousPage: boolean;
  startIndex: number;
  endIndex: number;
  itemsOnCurrentPage: number;
}

interface PaginationActions {
  nextPage: () => void;
  previousPage: () => void;
  goToPage: (page: number) => void;
  goToFirstPage: () => void;
  goToLastPage: () => void;
  reset: () => void;
}

interface UsePaginationResult {
  // Core pagination info
  pagination: PaginationInfo;
  
  // Actions
  actions: PaginationActions;
  
  // Utility methods
  currentPageItems: <T>(items: T[]) => T[];
  getPageItems: <T>(items: T[], page: number) => T[];
  getPageRange: (delta?: number) => number[];
}

export const usePagination = ({
  itemsPerPage,
  totalItems,
  initialPage = 0,
  onPageChange,
}: UsePaginationOptions): UsePaginationResult => {
  const [currentPage, setCurrentPage] = useState(initialPage);

  const totalPages = useMemo(() => {
    return Math.ceil(totalItems / itemsPerPage);
  }, [totalItems, itemsPerPage]);

  const hasNextPage = useMemo(() => {
    return currentPage < totalPages - 1;
  }, [currentPage, totalPages]);

  const hasPreviousPage = useMemo(() => {
    return currentPage > 0;
  }, [currentPage]);

  const startIndex = useMemo(() => {
    return currentPage * itemsPerPage;
  }, [currentPage, itemsPerPage]);

  const endIndex = useMemo(() => {
    return Math.min(startIndex + itemsPerPage, totalItems);
  }, [startIndex, itemsPerPage, totalItems]);

  const itemsOnCurrentPage = useMemo(() => {
    return endIndex - startIndex;
  }, [endIndex, startIndex]);

  // Internal setter that handles callback
  const setPage = useCallback((page: number) => {
    if (page >= 0 && page < totalPages && page !== currentPage) {
      setCurrentPage(page);
      onPageChange?.(page);
    }
  }, [totalPages, currentPage, onPageChange]);

  const nextPage = useCallback(() => {
    if (hasNextPage) {
      setPage(currentPage + 1);
    }
  }, [hasNextPage, currentPage, setPage]);

  const previousPage = useCallback(() => {
    if (hasPreviousPage) {
      setPage(currentPage - 1);
    }
  }, [hasPreviousPage, currentPage, setPage]);

  const goToPage = useCallback((page: number) => {
    setPage(page);
  }, [setPage]);

  const goToFirstPage = useCallback(() => {
    setPage(0);
  }, [setPage]);

  const goToLastPage = useCallback(() => {
    setPage(totalPages - 1);
  }, [setPage, totalPages]);

  const reset = useCallback(() => {
    setPage(initialPage);
  }, [setPage, initialPage]);

  const currentPageItems = useCallback(
    <T>(items: T[]) => {
      return items.slice(startIndex, endIndex);
    },
    [startIndex, endIndex],
  );

  const getPageItems = useCallback(
    <T>(items: T[], page: number) => {
      const pageStart = page * itemsPerPage;
      const pageEnd = Math.min(pageStart + itemsPerPage, items.length);
      return items.slice(pageStart, pageEnd);
    },
    [itemsPerPage],
  );

  const getPageRange = useCallback(
    (delta: number = 2) => {
      const start = Math.max(0, currentPage - delta);
      const end = Math.min(totalPages, currentPage + delta + 1);
      return Array.from({ length: end - start }, (_, i) => start + i);
    },
    [currentPage, totalPages],
  );

  const pagination: PaginationInfo = useMemo(() => ({
    currentPage,
    totalPages,
    hasNextPage,
    hasPreviousPage,
    startIndex,
    endIndex,
    itemsOnCurrentPage,
  }), [currentPage, totalPages, hasNextPage, hasPreviousPage, startIndex, endIndex, itemsOnCurrentPage]);

  const actions: PaginationActions = useMemo(() => ({
    nextPage,
    previousPage,
    goToPage,
    goToFirstPage,
    goToLastPage,
    reset,
  }), [nextPage, previousPage, goToPage, goToFirstPage, goToLastPage, reset]);

  return {
    pagination,
    actions,
    currentPageItems,
    getPageItems,
    getPageRange,
  };
};