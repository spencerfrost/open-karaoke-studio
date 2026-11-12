/**
 * SearchField - the add flow's search box, with suggestions while typing.
 *
 * Typing asks YouTube Music for suggestions (cheap, ~60 ms); results load only
 * when a suggestion is picked or the search is submitted. Built on shadcn's
 * Command for the listbox and its arrow-key navigation, which the stage's
 * keyboard also gets.
 *
 * Enter submits what was typed unless the arrow keys have picked a suggestion:
 * cmdk always highlights a first item, so its highlight only shows (and only
 * counts) once someone has moved it.
 */

import React, { useEffect, useRef, useState } from "react";
import {
  Command,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import { useDebouncedValue } from "@/hooks/useDebouncedValue";
import { useYoutubeMusicSuggestions } from "@/hooks/api/useYoutubeMusic";
import { cn } from "@/lib/utils";
import { ArrowUpRight, Search } from "lucide-react";

interface SearchFieldProps {
  /** The search the results show. */
  query: string;
  /** `picked`: the query is a suggestion someone chose, not what they typed. */
  onSearch: (query: string, how: "typed" | "picked") => void;
  autoFocus?: boolean;
}

/** "don't st" + "op me now": the typed part dim, the rest bold. */
const SuggestionText: React.FC<{ suggestion: string; typed: string }> = ({
  suggestion,
  typed,
}) => {
  const typedLower = typed.trim().toLowerCase();
  if (typedLower && suggestion.toLowerCase().startsWith(typedLower)) {
    return (
      <span className="flex-1 truncate">
        <span className="text-foreground-dim">
          {suggestion.slice(0, typedLower.length)}
        </span>
        <span className="font-bold">{suggestion.slice(typedLower.length)}</span>
      </span>
    );
  }
  return <span className="flex-1 truncate font-bold">{suggestion}</span>;
};

export const SearchField: React.FC<SearchFieldProps> = ({
  query,
  onSearch,
  autoFocus,
}) => {
  const [text, setText] = useState(query);
  const [focused, setFocused] = useState(false);
  const [navigated, setNavigated] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  // A search started elsewhere (a link, back) shows in the box.
  useEffect(() => setText(query), [query]);

  const trimmed = text.trim();
  const debounced = useDebouncedValue(trimmed, 150);
  const showSuggestions = focused && !!trimmed && trimmed !== query;
  const { data: suggestions = [] } = useYoutubeMusicSuggestions(
    debounced,
    showSuggestions,
  );

  const submit = (value: string, how: "typed" | "picked" = "typed") => {
    const next = value.trim();
    if (!next) return;
    setText(next);
    setNavigated(false);
    // Closes a phone's keyboard, and the suggestions with it.
    inputRef.current?.blur();
    onSearch(next, how);
  };

  return (
    <Command
      shouldFilter={false}
      disablePointerSelection
      label="Search for a song"
      data-navigated={navigated}
      className="group/search overflow-visible bg-transparent text-foreground"
      onKeyDown={(e) => {
        if (e.key === "ArrowDown" || e.key === "ArrowUp") setNavigated(true);
        if (e.key === "Escape") setNavigated(false);
        if (e.key === "Enter" && !(navigated && showSuggestions)) {
          e.preventDefault();
          submit(text);
        }
      }}
    >
      <CommandInput
        ref={inputRef}
        value={text}
        onValueChange={(value) => {
          setText(value);
          setNavigated(false);
        }}
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
        autoFocus={autoFocus}
        enterKeyHint="search"
        placeholder="Song or artist"
        aria-label="Song or artist"
        wrapperClassName={cn(
          "bg-surface text-surface-foreground h-14 rounded-xl border-2 px-4 transition-colors",
          "[&>svg]:text-primary [&>svg]:size-5 [&>svg]:opacity-100",
          showSuggestions ? "border-primary" : "border-border/60",
        )}
        className="h-full text-lg font-bold placeholder:text-foreground-faint placeholder:font-normal"
      />
      {showSuggestions && suggestions.length > 0 && (
        <CommandList
          // Keeps focus in the box, so picking doesn't blur it away first.
          onMouseDown={(e) => e.preventDefault()}
          className="bg-surface text-surface-foreground border-border/60 mt-2 max-h-none rounded-xl border"
        >
          {suggestions.map((suggestion) => (
            <CommandItem
              key={suggestion}
              value={suggestion}
              onSelect={() => submit(suggestion, "picked")}
              className={cn(
                "border-border/40 min-h-13 gap-3 rounded-none border-b px-4 text-lg last:border-b-0",
                "hover:bg-surface-hover data-[selected=true]:bg-transparent data-[selected=true]:text-inherit",
                "group-data-[navigated=true]/search:data-[selected=true]:bg-surface-hover",
              )}
            >
              <Search className="text-foreground-dim size-5" />
              <SuggestionText suggestion={suggestion} typed={text} />
              <ArrowUpRight className="text-foreground-dim size-5" />
            </CommandItem>
          ))}
        </CommandList>
      )}
    </Command>
  );
};
