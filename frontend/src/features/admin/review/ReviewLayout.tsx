import React, { useCallback, useEffect, useRef } from "react";
import { useSearchParams } from "react-router-dom";
import { cn } from "@/lib/utils";

/** What a list's detail side can do with the selection. */
export interface ReviewSelection {
  /** The item was dealt with: move on to the one after it. */
  done: () => void;
  /** Select another item by id (null clears the selection). */
  select: (id: string | null) => void;
}

interface ReviewLayoutProps<T> {
  /** undefined while loading or before a scan has run. */
  items: T[] | undefined;
  getId: (item: T) => string;
  /** One row's content; the row itself (button, selected look) is ours. */
  renderRow: (item: T) => React.ReactNode;
  /** Beside the row, outside its button: a checkbox, say. */
  renderRowLead?: (item: T) => React.ReactNode;
  /** The selected item. Remounted per item, so panels start fresh. */
  renderDetail: (item: T, selection: ReviewSelection) => React.ReactNode;
  /** What the list is about, a scan button: shown across the top. */
  toolbar?: React.ReactNode;
  /** Filter chips, between the toolbar and the list. */
  filters?: React.ReactNode;
  /** Shown instead of the split when there's nothing to list. */
  empty: React.ReactNode;
  isLoading?: boolean;
  error?: Error | null;
  /** Names the list for screen readers. */
  label: string;
}

const SELECTED_PARAM = "song";
const NARROW_QUERY = "(max-width: 1023px)";

/**
 * The review sections' shared shape: a list on the left, the selected item
 * on the right. The selection lives in the URL (`?song=<id>`, the item's
 * id: usually a song's, a report's or a folder's elsewhere), so a refresh or
 * a link keeps it. With nothing selected, or the selected item gone from
 * the list, the first item shows.
 *
 * Below laptop width the two stack, the selected item first.
 */
export function ReviewLayout<T>({
  items,
  getId,
  renderRow,
  renderRowLead,
  renderDetail,
  toolbar,
  filters,
  empty,
  isLoading,
  error,
  label,
}: ReviewLayoutProps<T>) {
  const [searchParams, setSearchParams] = useSearchParams();
  const selectedId = searchParams.get(SELECTED_PARAM);
  const detailRef = useRef<HTMLDivElement>(null);

  const selected =
    items?.find((item) => getId(item) === selectedId) ?? items?.[0];
  const shownId = selected ? getId(selected) : null;

  const select = useCallback(
    (id: string | null) => {
      setSearchParams(
        (params) => {
          const next = new URLSearchParams(params);
          if (id) next.set(SELECTED_PARAM, id);
          else next.delete(SELECTED_PARAM);
          return next;
        },
        // Picking rows isn't navigation; back leaves the section.
        { replace: true },
      );
    },
    [setSearchParams],
  );

  // `done` runs from a mutation's callback, after renders this closure
  // didn't see; read the list as it is now.
  const latest = useRef({ items, shownId });
  useEffect(() => {
    latest.current = { items, shownId };
  });

  const done = useCallback(() => {
    const { items: current, shownId: currentId } = latest.current;
    if (!current?.length) return select(null);
    const index = current.findIndex((item) => getId(item) === currentId);
    const next = current[index + 1] ?? current[index - 1];
    select(next && index !== -1 ? getId(next) : null);
  }, [getId, select]);

  const pick = (id: string) => {
    select(id);
    // Stacked: the song sits above the list, so bring it into view.
    if (window.matchMedia(NARROW_QUERY).matches) {
      detailRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  };

  let body: React.ReactNode;
  if (error) {
    body = (
      <p className="text-sm text-destructive-strong">
        Couldn&apos;t load this list: {error.message}
      </p>
    );
  } else if (isLoading) {
    body = <p className="py-12 text-center text-muted-foreground">Loading…</p>;
  } else if (!items?.length || !selected) {
    body = empty;
  } else {
    body = (
      <div className="flex flex-col gap-6 lg:grid lg:grid-cols-[minmax(16rem,22rem)_minmax(0,1fr)] lg:items-start">
        <ul
          aria-label={label}
          className="order-last divide-y divide-border/50 overflow-hidden rounded-lg border border-border/60 lg:order-none"
        >
          {items.map((item) => {
            const id = getId(item);
            const isSelected = id === shownId;
            return (
              <li
                key={id}
                className={cn(
                  "flex items-center transition-colors",
                  isSelected
                    ? "bg-primary/15 shadow-[inset_3px_0_0_var(--color-primary)]"
                    : "hover:bg-muted/40",
                )}
              >
                {renderRowLead && (
                  <div className="flex shrink-0 pl-3">
                    {renderRowLead(item)}
                  </div>
                )}
                <button
                  type="button"
                  aria-current={isSelected ? "true" : undefined}
                  onClick={() => pick(id)}
                  className="block min-w-0 flex-1 px-3 py-2.5 text-left"
                >
                  {renderRow(item)}
                </button>
              </li>
            );
          })}
        </ul>

        <div
          ref={detailRef}
          className="min-w-0 scroll-mt-4 rounded-lg border border-border/60 bg-card p-4 text-card-foreground md:p-6 lg:sticky lg:top-0 lg:max-h-[calc(100vh-4rem)] lg:overflow-y-auto"
        >
          <React.Fragment key={shownId}>
            {renderDetail(selected, { done, select })}
          </React.Fragment>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {toolbar}
      {filters}
      {body}
    </div>
  );
}

interface FilterChip {
  value: string;
  label: string;
  count?: number;
}

/** A row of chips; one is on at a time. */
export const FilterChips: React.FC<{
  chips: FilterChip[];
  value: string;
  onChange: (value: string) => void;
  label: string;
}> = ({ chips, value, onChange, label }) => (
  <div role="group" aria-label={label} className="flex flex-wrap gap-2">
    {chips.map((chip) => {
      const isOn = chip.value === value;
      return (
        <button
          key={chip.value}
          type="button"
          aria-pressed={isOn}
          onClick={() => onChange(chip.value)}
          className={cn(
            "rounded-full border px-3 py-1 text-sm font-medium transition-colors",
            isOn
              ? "border-primary/50 bg-primary/15 text-primary"
              : "border-border bg-muted text-muted-foreground hover:bg-muted/80",
          )}
        >
          {chip.label}
          {chip.count !== undefined && (
            <span className="ml-1.5 tabular-nums opacity-80">{chip.count}</span>
          )}
        </button>
      );
    })}
  </div>
);

/** A centered note for an empty list or a scan that hasn't run. */
export const ReviewEmpty: React.FC<{
  icon: React.ComponentType<{ className?: string }>;
  title?: string;
  children: React.ReactNode;
}> = ({ icon: Icon, title, children }) => (
  <div className="py-12 text-center text-muted-foreground">
    <Icon className="mx-auto mb-3 h-10 w-10 opacity-40" />
    {title && <p className="font-medium">{title}</p>}
    <p className="text-sm">{children}</p>
  </div>
);
