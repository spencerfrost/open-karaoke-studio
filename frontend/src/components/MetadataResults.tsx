import React from "react";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Label } from "@/components/ui/label";
import { Card, CardContent } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Loader2 } from "lucide-react";
import type { MetadataOption } from "@/hooks/api/useMetadata";

interface MetadataResultsProps {
  options: MetadataOption[];
  selectedOption?: MetadataOption | null;
  onSelectionChange: (option: MetadataOption) => void;
  isLoading?: boolean;
  autoSelectFirst?: boolean;
  emptyMessage?: string;
  className?: string;
}

export const MetadataResults: React.FC<MetadataResultsProps> = ({
  options,
  selectedOption,
  onSelectionChange,
  isLoading = false,
  autoSelectFirst = true,
  emptyMessage = "No metadata found",
  className = "",
}) => {
  // Auto-select first option if enabled and no selection exists
  React.useEffect(() => {
    if (autoSelectFirst && options.length > 0 && !selectedOption) {
      onSelectionChange(options[0]);
    }
  }, [options, selectedOption, autoSelectFirst, onSelectionChange]);

  const handleValueChange = (value: string) => {
    const index = parseInt(value);
    const selected = options[index];
    if (selected) {
      onSelectionChange(selected);
    }
  };

  const getSelectedIndex = () => {
    if (!selectedOption) return "0";
    const index = options.findIndex((option) =>
      option.metadataId
        ? option.metadataId === selectedOption.metadataId
        : option === selectedOption
    );
    return index >= 0 ? String(index) : "0";
  };

  if (isLoading) {
    return (
      <div
        className={`flex flex-col items-center justify-center py-8 ${className}`}
      >
        <Loader2 className="h-8 w-8 animate-spin mb-4 text-primary" />
        <p className="text-center font-medium">Loading metadata options...</p>
        <p className="text-center text-sm text-muted-foreground mt-1">
          Searching music databases for the best match
        </p>
      </div>
    );
  }

  if (options.length === 0) {
    return (
      <Card className={className}>
        <CardContent className="py-4">
          <p className="text-muted-foreground text-center">{emptyMessage}</p>
          <p className="text-xs text-muted-foreground text-center mt-2">
            Try adjusting your search terms or check the spelling
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <ScrollArea className={`flex-1 pr-4 ${className}`}>
      <RadioGroup
        value={getSelectedIndex()}
        onValueChange={handleValueChange}
        className="space-y-4"
      >
        {options.map((option, index) => (
          <div
            key={option.metadataId || index}
            className="flex items-center space-x-2"
          >
            <RadioGroupItem value={String(index)} id={`metadata-${index}`} />
            <div className="flex-1">
              <Label
                htmlFor={`metadata-${index}`}
                className="flex flex-col space-y-1 cursor-pointer"
              >
                <Card
                  className={`hover:border-primary w-full ${
                    selectedOption === option
                      ? "border-primary bg-primary/5"
                      : ""
                  }`}
                >
                  <CardContent className="p-3">
                    <div className="flex justify-between items-start">
                      <div className="flex-1">
                        <h4 className="font-medium text-sm">{option.title}</h4>
                        <p className="text-sm text-muted-foreground">
                          {option.artist}
                          {option.album && ` • ${option.album}`}
                        </p>
                        {(option.releaseYear || option.genre) && (
                          <div className="mt-1 flex flex-wrap gap-1">
                            {option.releaseYear && (
                              <span className="px-2 py-0.5 text-xs bg-secondary rounded-full">
                                {option.releaseYear}
                              </span>
                            )}
                            {option.genre && (
                              <span className="px-2 py-0.5 text-xs bg-secondary rounded-full">
                                {option.genre}
                              </span>
                            )}
                          </div>
                        )}
                      </div>
                      <div className="flex flex-col items-end gap-1">
                        {option.artworkUrl && (
                          <img
                            src={option.artworkUrl}
                            alt={`${option.title} cover`}
                            className="w-12 h-12 rounded object-cover"
                          />
                        )}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </Label>
            </div>
          </div>
        ))}
      </RadioGroup>
    </ScrollArea>
  );
};
