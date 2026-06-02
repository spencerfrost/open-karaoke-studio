import React from "react";

interface AlphabeticalNavigationProps {
  availableLetters: string[];
  onLetterClick: (letter: string) => void;
  className?: string;
}

const AlphabeticalNavigation: React.FC<AlphabeticalNavigationProps> = ({
  availableLetters,
  onLetterClick,
  className = "",
}) => {
  const allLetters = [
    "#",
    "A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M",
    "N", "O", "P", "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z",
  ];

  return (
    <div
      className={`flex flex-col h-full gap-1 ${className}`}
      data-available-letters={availableLetters.length}
    >
      {allLetters.map((letter) => {
        return (
          <div key={letter} className="relative group flex-1">
            <button
              onClick={() => onLetterClick(letter)}
              className="w-7 p-0 text-s rounded bg-transparent text-lemon-chiffon hover:bg-orange-peel/40"
              aria-label={`Jump to ${letter}`}
            >
              {letter}
            </button>
            <div
              className="pointer-events-none absolute right-full top-1/2 mr-2 -translate-y-1/2 rounded bg-rust px-3 py-1 text-3xl font-bold text-lemon-chiffon opacity-0 shadow-md transition-opacity duration-150 group-hover:opacity-100 group-focus-within:opacity-100"
              aria-hidden="true"
            >
              {letter}
            </div>
          </div>
        );
      })}
    </div>
  );
};

export default AlphabeticalNavigation;
