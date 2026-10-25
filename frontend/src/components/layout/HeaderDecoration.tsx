/**
 * HeaderDecoration - the theme's mark under a screen's title.
 *
 * One element; each theme decides what it looks like in index.css
 * (`.header-decoration`), or hides it. Purely decorative.
 */

import React from "react";
import { cn } from "@/lib/utils";

export const HeaderDecoration: React.FC<{ className?: string }> = ({
  className,
}) => <div aria-hidden="true" className={cn("header-decoration", className)} />;
