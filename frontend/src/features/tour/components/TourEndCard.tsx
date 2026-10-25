/**
 * TourEndCard - the last step: what it's built with, where the code and docs
 * are, and "Keep exploring", which ends the tour.
 */

import React from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { END_COPY } from "../tourCopy";
import { docsLink } from "../tourSteps";
import TourCard from "./TourCard";

const DOCS_URL = import.meta.env.VITE_DOCS_URL;

const TourEndCard: React.FC<{ onFinish: () => void }> = ({ onFinish }) => {
  const docs = docsLink(DOCS_URL, "");

  return (
    <TourCard title={END_COPY.title} body={END_COPY.body}>
      <div className="flex flex-col gap-2">
        <h3 className="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">
          Built with
        </h3>
        <ul className="flex flex-wrap gap-1.5">
          {END_COPY.stack.map((item) => (
            <li key={item}>
              <Badge variant="secondary">{item}</Badge>
            </li>
          ))}
        </ul>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <Button variant="primary" onClick={onFinish}>
          Keep exploring
        </Button>
        <Button variant="outline" asChild>
          <a href={END_COPY.repoUrl} target="_blank" rel="noreferrer">
            Code on GitHub
          </a>
        </Button>
        {docs && (
          <Button variant="outline" asChild>
            <a href={docs} target="_blank" rel="noreferrer">
              Read the docs
            </a>
          </Button>
        )}
      </div>
    </TourCard>
  );
};

export default TourEndCard;
