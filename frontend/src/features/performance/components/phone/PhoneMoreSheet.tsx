/**
 * PhoneMoreSheet - everything a singer needs once, not every line: lyrics
 * repairs, reports, lyrics size, auto-scroll and the music volume.
 *
 * Saving goes through useLyricsFixes, the same code the stage rail uses. The
 * search and paste dialogs open after the sheet closes, rather than stacking
 * a dialog on a drawer.
 */

import React, { useState } from "react";
import { ClipboardPaste, Search } from "lucide-react";
import { useShallow } from "zustand/react/shallow";
import { Button } from "@/components/ui/button";
import {
  Drawer,
  DrawerContent,
  DrawerHeader,
  DrawerTitle,
} from "@/components/ui/drawer";
import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";
import { Switch } from "@/components/ui/switch";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import LyricsFetchDialog from "@/features/lyrics/components/LyricsFetchDialog";
import PasteLyricsDialog from "@/features/lyrics/components/PasteLyricsDialog";
import { useKaraokePlayerStore } from "@/stores/useKaraokePlayerStore";
import {
  formatLyricsOffset,
  getLyricsSizeLabel,
  type LyricsSize,
} from "@/utils/performanceControls";
import { LYRICS_REPORTS, useLyricsFixes } from "../../hooks/useLyricsFixes";
import { phoneSectionLabelClass } from "./phoneStyles";

const SIZES: LyricsSize[] = ["small", "medium", "large"];

const rowButtonClass =
  "h-13 w-full justify-start gap-2.5 rounded-md border border-glass-border/20 px-3.5 text-lg font-semibold text-foreground";

interface PhoneMoreSheetProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

const PhoneMoreSheet: React.FC<PhoneMoreSheetProps> = ({
  open,
  onOpenChange,
}) => {
  const fixes = useLyricsFixes();
  const {
    lyricsOffset,
    lyricsSize,
    setLyricsSize,
    autoScrollEnabled,
    setAutoScrollEnabled,
    instrumentalVolume,
    setInstrumentalVolume,
  } = useKaraokePlayerStore(
    useShallow((s) => ({
      lyricsOffset: s.lyricsOffset,
      lyricsSize: s.lyricsSize,
      setLyricsSize: s.setLyricsSize,
      autoScrollEnabled: s.autoScrollEnabled,
      setAutoScrollEnabled: s.setAutoScrollEnabled,
      instrumentalVolume: s.instrumentalVolume,
      setInstrumentalVolume: s.setInstrumentalVolume,
    })),
  );

  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [isPasteOpen, setIsPasteOpen] = useState(false);

  const openDialog = (setDialogOpen: (open: boolean) => void) => {
    onOpenChange(false);
    setDialogOpen(true);
  };

  return (
    <>
      <Drawer open={open} onOpenChange={onOpenChange}>
        <DrawerContent className="max-h-[88dvh] border-glass-border/10 bg-overlay/95 text-foreground backdrop-blur-md">
          <div className="overflow-y-auto pb-[max(1.25rem,env(safe-area-inset-bottom))]">
            <DrawerHeader className="flex-row items-center justify-between pb-2 text-left">
              <DrawerTitle className="font-display text-lg">More</DrawerTitle>
              <Button
                variant="ghost"
                onClick={() => onOpenChange(false)}
                className="h-11 px-3 text-base font-semibold"
              >
                Done
              </Button>
            </DrawerHeader>

            <div className="mx-auto flex w-full max-w-2xl flex-col gap-5 px-4 pb-2">
              <section className="flex flex-col gap-2">
                <h2 className={phoneSectionLabelClass}>Lyrics on screen</h2>
                {fixes.canSaveOffset && (
                  <Button
                    variant="primary"
                    disabled={fixes.isSaving}
                    onClick={fixes.saveOffset}
                    className="h-13 w-full text-lg font-semibold"
                  >
                    Keep {formatLyricsOffset(lyricsOffset)} for this song
                  </Button>
                )}
                <Button
                  variant="ghost"
                  disabled={!fixes.song}
                  onClick={() => openDialog(setIsSearchOpen)}
                  className={rowButtonClass}
                >
                  <Search className="size-5" />
                  Find different lyrics
                </Button>
                <Button
                  variant="ghost"
                  disabled={!fixes.song}
                  onClick={() => openDialog(setIsPasteOpen)}
                  className={rowButtonClass}
                >
                  <ClipboardPaste className="size-5" />
                  Paste lyrics
                </Button>
              </section>

              {fixes.hasLyrics && (
                <section className="flex flex-col gap-2">
                  <h2 className={phoneSectionLabelClass}>Something wrong?</h2>
                  <div className="grid grid-cols-2 gap-2">
                    {LYRICS_REPORTS.map(({ kind, label }) => {
                      const isReported = fixes.reported.has(kind);
                      return (
                        <Button
                          key={kind}
                          variant="ghost"
                          disabled={
                            !fixes.songId || fixes.isReporting || isReported
                          }
                          onClick={() => fixes.report(kind)}
                          className="h-13 rounded-md border border-glass-border/20 text-lg font-semibold text-foreground"
                        >
                          {isReported ? "Reported" : label}
                        </Button>
                      );
                    })}
                  </div>
                </section>
              )}

              <section className="flex flex-col gap-2">
                <h2 className={phoneSectionLabelClass}>Lyrics size</h2>
                <ToggleGroup
                  type="single"
                  spacing={2}
                  value={lyricsSize}
                  onValueChange={(value) => {
                    // Radix clears the value on a second tap; keep a size.
                    if (value) setLyricsSize(value as LyricsSize);
                  }}
                  className="grid w-full grid-cols-3"
                  aria-label="Lyrics size"
                >
                  {SIZES.map((size) => (
                    <ToggleGroupItem
                      key={size}
                      value={size}
                      className="h-13 w-full rounded-md border border-glass-border/20 text-lg font-semibold text-foreground data-[state=on]:border-primary data-[state=on]:bg-primary/15 data-[state=on]:text-foreground"
                    >
                      {getLyricsSizeLabel(size)}
                    </ToggleGroupItem>
                  ))}
                </ToggleGroup>
              </section>

              <div className="flex min-h-13 items-center justify-between gap-3">
                <Label
                  htmlFor="phone-lyrics-auto-scroll"
                  className="text-lg font-semibold text-foreground"
                >
                  Scroll lyrics automatically
                </Label>
                <Switch
                  id="phone-lyrics-auto-scroll"
                  checked={autoScrollEnabled}
                  onCheckedChange={setAutoScrollEnabled}
                />
              </div>

              <section className="flex flex-col gap-3">
                <h2 className={phoneSectionLabelClass}>
                  Music volume · {Math.round(instrumentalVolume * 100)}%
                </h2>
                <Slider
                  value={[instrumentalVolume]}
                  min={0}
                  max={1}
                  step={0.05}
                  orientation="horizontal"
                  onValueChange={([v]) => setInstrumentalVolume(v)}
                  className="h-11"
                  aria-label="Music volume"
                />
              </section>
            </div>
          </div>
        </DrawerContent>
      </Drawer>

      {fixes.songForDialog && (
        <>
          <LyricsFetchDialog
            isOpen={isSearchOpen}
            onClose={() => setIsSearchOpen(false)}
            song={fixes.songForDialog}
            onLyricsSelected={(result) =>
              fixes.applySearchResult(result, () => setIsSearchOpen(false))
            }
          />
          <PasteLyricsDialog
            isOpen={isPasteOpen}
            onClose={() => setIsPasteOpen(false)}
            onLyricsConfirmed={(text) =>
              fixes.applyPaste(text, () => setIsPasteOpen(false))
            }
          />
        </>
      )}
    </>
  );
};

export default PhoneMoreSheet;
