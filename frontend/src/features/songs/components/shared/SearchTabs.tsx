import React from "react";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Music, Video } from "lucide-react";
import { SearchTabsProps } from "./types";

export const SearchTabs: React.FC<SearchTabsProps> = ({
  activeSource,
  onSourceChange,
  counts,
}) => {
  return (
    <Tabs
      value={activeSource}
      onValueChange={(value) => onSourceChange(value as typeof activeSource)}
      className="w-full"
    >
      <TabsList className="grid w-full grid-cols-2">
        <TabsTrigger value="youtube-music" className="flex items-center gap-2">
          <Music className="h-4 w-4" />
          YouTube Music
          {counts["youtube-music"] > 0 && (
            <Badge variant="secondary" className="ml-1 text-xs">
              {counts["youtube-music"]}
            </Badge>
          )}
        </TabsTrigger>
        <TabsTrigger value="youtube" className="flex items-center gap-2">
          <Video className="h-4 w-4" />
          YouTube
          {counts["youtube"] > 0 && (
            <Badge variant="secondary" className="ml-1 text-xs">
              {counts["youtube"]}
            </Badge>
          )}
        </TabsTrigger>
      </TabsList>
    </Tabs>
  );
};
