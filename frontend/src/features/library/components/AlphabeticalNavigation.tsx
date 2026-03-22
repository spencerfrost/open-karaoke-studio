import React, { useEffect, useState } from "react";

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
  const [activeSection, setActiveSection] = useState<string>("");

  const allLetters = [
    "#",
    "A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M",
    "N", "O", "P", "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z",
  ];

  // Observe which section is currently in view
  useEffect(() => {
    const observers = new Map<string, IntersectionObserver>();

    availableLetters.forEach((letter) => {
      const element = document.getElementById(`artist-section-${letter}`);
      if (element) {
        const observer = new IntersectionObserver(
          (entries) => {
            entries.forEach((entry) => {
              if (entry.isIntersecting) {
                setActiveSection(letter);
              }
            });
          },
          {
            rootMargin: "-20% 0px -80% 0px",
            threshold: 0.1,
          },
        );
        observer.observe(element);
        observers.set(letter, observer);
      }
    });

    return () => {
      observers.forEach((observer) => observer.disconnect());
    };
  }, [availableLetters]);

  return (
    <div className={`flex flex-col gap-1 ${className}`}>
      {allLetters.map((letter) => {
        return (
          <button
            key={letter}
            onClick={() => onLetterClick(letter)}
            className={`w-6 h-6 text-xs rounded bg-orange-peel/20 text-orange-peel hover:bg-orange-peel/40 hover:scale-105 ${activeSection === letter ? "bg-orange-peel/40" : ""}`}
            title={`Jump to ${letter}`}
          >
            {letter}
          </button>
        );
      })}
    </div>
  );
};

export default AlphabeticalNavigation;
