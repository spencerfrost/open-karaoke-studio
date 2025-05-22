// frontend/src/components/upload/MetadataTab.tsx
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Label } from "@/components/ui/label";
import { Card, CardContent } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Loader2 } from "lucide-react";
import { MetadataOption } from "@/hooks/useYoutube";

interface MetadataTabProps {
  isLoading: boolean;
  options: MetadataOption[];
  selectedOption: MetadataOption | null;
  onSelectionChange: (option: MetadataOption) => void;
}

export function MetadataTab({
  isLoading,
  options,
  selectedOption,
  onSelectionChange,
}: MetadataTabProps) {
  const handleValueChange = (value: string) => {
    const index = parseInt(value);
    const selected = options[index];
    if (selected) {
      onSelectionChange(selected);
    }
  };

  return (
    <ScrollArea className="flex-1 pr-4">
      {isLoading ? (
        <div className="flex flex-col items-center justify-center py-8">
          <Loader2 className="h-8 w-8 animate-spin mb-4 text-primary" />
          <p className="text-center font-medium">Loading metadata options...</p>
          <p className="text-center text-sm text-muted-foreground mt-1">
            Searching music databases for the best match
          </p>
        </div>
      ) : options.length === 0 ? (
        <Card>
          <CardContent className="py-4">
            <p className="text-muted-foreground text-center">
              No additional metadata found
            </p>
            <p className="text-xs text-muted-foreground text-center mt-2">
              We'll use the information you provided in the previous step
            </p>
          </CardContent>
        </Card>
      ) : (
        <RadioGroup
          value={String(options.indexOf(selectedOption || options[0]))}
          onValueChange={handleValueChange}
          className="space-y-4"
        >
          {options.map((option, index) => (
            <div key={option.id || index} className="flex items-start space-x-2">
              <RadioGroupItem value={String(index)} id={`metadata-${index}`} className="mt-1" />
              <div className="flex-1">
                <Label
                  htmlFor={`metadata-${index}`}
                  className="flex flex-col space-y-1 cursor-pointer"
                >
                  <Card className={`hover:border-primary ${selectedOption === option ? 'border-primary bg-primary/5' : ''}`}>
                    <CardContent className="p-3">
                      <div className="flex justify-between items-start">
                        <div className="flex-1">
                          <h4 className="font-medium text-sm">{option.title}</h4>
                          <p className="text-sm text-muted-foreground">
                            {option.artist}
                            {option.album && ` • ${option.album}`}
                          </p>
                          {(option.year || option.genre || option.language) && (
                            <div className="mt-1 flex flex-wrap gap-1">
                              {option.year && (
                                <span className="px-2 py-0.5 text-xs bg-secondary rounded-full">
                                  {option.year}
                                </span>
                              )}
                              {option.genre && (
                                <span className="px-2 py-0.5 text-xs bg-secondary rounded-full">
                                  {option.genre}
                                </span>
                              )}
                              {option.language && (
                                <span className="px-2 py-0.5 text-xs bg-secondary rounded-full">
                                  {option.language}
                                </span>
                              )}
                            </div>
                          )}
                        </div>
                        {option.source && (
                          <span className="text-xs bg-muted px-2 py-1 rounded text-muted-foreground">
                            {option.source}
                          </span>
                        )}
                      </div>
                    </CardContent>
                  </Card>
                </Label>
              </div>
            </div>
          ))}
        </RadioGroup>
      )}
    </ScrollArea>
  );
}
