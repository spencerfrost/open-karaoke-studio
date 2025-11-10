import React, { useEffect, useState } from "react";

interface AlphabeticalNavigationProps {
  availableLetters: string[];
  onLetterClick: (letter: string) => void;
  className?: string;
  isMobile?: boolean;
}

const AlphabeticalNavigation: React.FC<AlphabeticalNavigationProps> = ({
  availableLetters,
  onLetterClick,
  className = "",
  isMobile = false,
}) => {
  const [activeSection, setActiveSection] = useState<string>("");

  // All letters A-Z plus special characters
  const allLetters = [
    "A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M",
    "N", "O", "P", "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z", "#"
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
            rootMargin: "-20% 0px -80% 0px", // Trigger when section is near the top
            threshold: 0.1,
          }
        );
        observer.observe(element);
        observers.set(letter, observer);
      }
    });

    return () => {
      observers.forEach((observer) => observer.disconnect());
    };
  }, [availableLetters]);

  const handleLetterClick = (letter: string) => {
    if (availableLetters.includes(letter)) {
      onLetterClick(letter);
    }
  };

  return (
    <div className={`${isMobile ? 'sticky top-16 z-20' : 'sticky top-24'} ${className}`}>
      <div className="bg-dark-cyan/90 backdrop-blur-sm border border-orange-peel/30 rounded-lg p-2 shadow-lg">
        <div className={`${isMobile ? 'flex gap-1 overflow-x-auto scrollbar-hide pb-1' : 'flex flex-col gap-1'}`}>
          {allLetters.map((letter) => {
            const isAvailable = availableLetters.includes(letter);
            const isActive = letter === activeSection;
            
            return (
              <button
                key={letter}
                onClick={() => handleLetterClick(letter)}
                disabled={!isAvailable}
                className={`
                  ${isMobile ? 'w-7 h-7 text-xs flex-shrink-0' : 'w-8 h-8 text-sm'} 
                  font-medium rounded transition-all duration-200
                  ${isAvailable
                    ? isActive
                      ? "bg-orange-peel text-dark-cyan shadow-md scale-110"
                      : "bg-orange-peel/20 text-orange-peel hover:bg-orange-peel/40 hover:scale-105"
                    : "text-gray-500 cursor-not-allowed opacity-50"
                  }
                `}
                title={isAvailable ? `Jump to ${letter}` : `No artists starting with ${letter}`}
              >
                {letter}
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
};

export default AlphabeticalNavigation;