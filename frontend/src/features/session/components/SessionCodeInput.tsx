import React from "react";
import { REGEXP_ONLY_CHARS } from "input-otp";
import {
  InputOTP,
  InputOTPGroup,
  InputOTPSlot,
} from "@/components/ui/input-otp";
import { cn } from "@/lib/utils";

export const SESSION_CODE_LENGTH = 4;

interface SessionCodeInputProps {
  id?: string;
  value: string;
  onChange: (code: string) => void;
  /** "card" sits on the cream card (large boxes); "page" sits on the page
   * background as a compact row. */
  variant?: "card" | "page";
  autoFocus?: boolean;
  /** Called when the last letter goes in, e.g. to move focus to the name. */
  onComplete?: () => void;
}

/**
 * SessionCodeInput - the 4-letter session code, one box per letter.
 * Letters only, always uppercase; a pasted code is cleaned up the same way.
 */
export const SessionCodeInput: React.FC<SessionCodeInputProps> = ({
  id,
  value,
  onChange,
  variant = "card",
  autoFocus = false,
  onComplete,
}) => (
  <InputOTP
    id={id}
    maxLength={SESSION_CODE_LENGTH}
    pattern={REGEXP_ONLY_CHARS}
    pasteTransformer={(pasted) => pasted.replace(/[^a-zA-Z]/g, "")}
    value={value}
    onChange={(code) => onChange(code.toUpperCase())}
    onComplete={onComplete}
    autoFocus={autoFocus}
    autoComplete="off"
    autoCapitalize="characters"
    autoCorrect="off"
    spellCheck={false}
    inputMode="text"
    containerClassName={variant === "card" ? "w-full" : undefined}
  >
    <InputOTPGroup
      className={cn(
        variant === "card" ? "grid w-full grid-cols-4 gap-2.5" : "gap-2",
      )}
    >
      {Array.from({ length: SESSION_CODE_LENGTH }, (_, index) => (
        <InputOTPSlot
          key={index}
          index={index}
          className={cn(
            // Separate boxes rather than shadcn's joined segments.
            "rounded-lg border-2 font-accent uppercase shadow-none first:rounded-lg first:border-l-2 last:rounded-lg",
            "data-[active=true]:border-primary data-[active=true]:ring-primary/30",
            variant === "card"
              ? // The slot's caret is bg-foreground (page text); on the card
                // it needs the card's text color.
                "h-20 w-full border-card-border text-6xl text-card-foreground [--foreground:var(--card-foreground)]"
              : "h-15 w-13 border-foreground-faint bg-surface-sunk text-5xl text-foreground",
          )}
        />
      ))}
    </InputOTPGroup>
  </InputOTP>
);
