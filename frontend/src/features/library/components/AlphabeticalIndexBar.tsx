import React, { useCallback, useEffect, useRef, useState } from "react";

interface AlphabeticalIndexBarProps {
  availableLetters: string[];
  onLetterClick: (letter: string) => void;
  className?: string;
}

const ALL_LETTERS = [
  "#",
  "A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M",
  "N", "O", "P", "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z",
];

function clamp(value: number, min: number, max: number) {
  return Math.min(Math.max(value, min), max);
}

const AlphabeticalIndexBar: React.FC<AlphabeticalIndexBarProps> = ({
  availableLetters,
  onLetterClick,
  className = "",
}) => {
  const [activeSection, setActiveSection] = useState<string>("");
  const [activeLetter, setActiveLetter] = useState<string | null>(null);
  const barRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const observers = new Map<string, IntersectionObserver>();

    availableLetters.forEach((letter) => {
      const element = document.getElementById(`artist-section-${letter}`);
      if (element) {
        const observer = new IntersectionObserver(
          (entries) => {
            entries.forEach((entry) => {
              if (entry.isIntersecting) setActiveSection(letter);
            });
          },
          { rootMargin: "-20% 0px -80% 0px", threshold: 0.1 },
        );
        observer.observe(element);
        observers.set(letter, observer);
      }
    });

    return () => observers.forEach((o) => o.disconnect());
  }, [availableLetters]);

  const getLetterFromY = useCallback((clientY: number): string => {
    const rect = barRef.current!.getBoundingClientRect();
    const ratio = clamp((clientY - rect.top) / rect.height, 0, 1);
    return ALL_LETTERS[Math.floor(ratio * ALL_LETTERS.length)];
  }, []);

  const getNearestAvailable = useCallback(
    (letter: string): string | null => {
      if (!availableLetters.length) return null;
      const idx = ALL_LETTERS.indexOf(letter);
      if (idx === -1) return availableLetters[0];

      for (let offset = 0; offset < ALL_LETTERS.length; offset++) {
        const above = ALL_LETTERS[idx - offset];
        if (above && availableLetters.includes(above)) return above;
        const below = ALL_LETTERS[idx + offset];
        if (below && availableLetters.includes(below)) return below;
      }
      return null;
    },
    [availableLetters],
  );

  const handleInteraction = useCallback(
    (clientY: number) => {
      const letter = getLetterFromY(clientY);
      const nearest = getNearestAvailable(letter);
      setActiveLetter(letter);
      if (nearest) onLetterClick(nearest);
    },
    [getLetterFromY, getNearestAvailable, onLetterClick],
  );

  const handleTouch = useCallback(
    (e: React.TouchEvent) => {
      e.preventDefault();
      handleInteraction(e.touches[0].clientY);
    },
    [handleInteraction],
  );

  const handleClick = useCallback(
    (e: React.MouseEvent) => {
      handleInteraction(e.clientY);
    },
    [handleInteraction],
  );

  return (
    <div className={`relative flex items-center h-full ${className}`}>
      {activeLetter && (
        <div className="absolute right-full mr-3 w-12 h-12 rounded-full bg-orange-peel flex items-center justify-center text-white text-xl font-bold shadow-lg pointer-events-none select-none">
          {activeLetter}
        </div>
      )}

      <div
        ref={barRef}
        className="flex flex-col items-center justify-between h-full py-2 px-1 cursor-pointer select-none"
        style={{ touchAction: "none" }}
        onTouchStart={handleTouch}
        onTouchMove={handleTouch}
        onTouchEnd={() => setActiveLetter(null)}
        onClick={handleClick}
      >
        {ALL_LETTERS.map((letter) => {
          const available = availableLetters.includes(letter);
          const active = activeSection === letter;
          return (
            <span
              key={letter}
              className={`text-[10px] leading-tight w-4 text-center transition-colors ${
                active
                  ? "text-orange-peel font-bold"
                  : available
                    ? "text-orange-peel/80"
                    : "text-white/20"
              }`}
            >
              {letter}
            </span>
          );
        })}
      </div>
    </div>
  );
};

export default AlphabeticalIndexBar;
