/**
 * TourCard - one step's words: title, the plain line, anything the step adds,
 * the "how this works" line for a technical reader, and Skip tour.
 */

import React from "react";
import { Button } from "@/components/ui/button";
import {
  PopoverDescription,
  PopoverHeader,
  PopoverTitle,
} from "@/components/ui/popover";
import { Separator } from "@/components/ui/separator";
import { docsLink } from "../tourSteps";

const DOCS_URL = import.meta.env.VITE_DOCS_URL;

interface TourCardProps {
  title: string;
  body: string;
  how?: string;
  docsPage?: string;
  /** Step-specific content under the body: a button, a song to sing. */
  children?: React.ReactNode;
  onSkip?: () => void;
}

const TourCard: React.FC<TourCardProps> = ({
  title,
  body,
  how,
  docsPage,
  children,
  onSkip,
}) => {
  const docs = docsLink(DOCS_URL, docsPage);

  return (
    <div className="flex flex-col gap-4">
      <PopoverHeader className="gap-2">
        <PopoverTitle className="font-display text-xl font-bold leading-tight">
          {title}
        </PopoverTitle>
        <PopoverDescription className="text-base text-popover-foreground">
          {body}
        </PopoverDescription>
      </PopoverHeader>

      {children}

      {how && (
        <>
          <Separator />
          <p className="text-sm text-muted-foreground">
            <span className="font-semibold">How this works: </span>
            {how}
            {docs && (
              <>
                {" "}
                <a
                  href={docs}
                  target="_blank"
                  rel="noreferrer"
                  className="text-primary underline-offset-4 hover:underline"
                >
                  Read the docs
                </a>
              </>
            )}
          </p>
        </>
      )}

      {onSkip && (
        <div className="flex justify-end">
          <Button
            variant="link"
            size="sm"
            onClick={onSkip}
            className="h-auto p-0 text-muted-foreground hover:text-foreground"
          >
            Skip tour
          </Button>
        </div>
      )}
    </div>
  );
};

export default TourCard;
