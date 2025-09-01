import React from "react";
import { Input } from "@/components/ui/input";
import { SearchInputProps } from "./YouTubeMusicSearch.types";

export const SearchInput: React.FC<SearchInputProps> = ({
  query,
  onQueryChange,
  placeholder = "Search for official audio...",
}) => {
  return (
    <Input
      type="text"
      placeholder={placeholder}
      value={query}
      onChange={(e) => onQueryChange(e.target.value)}
      className="mb-4"
    />
  );
};