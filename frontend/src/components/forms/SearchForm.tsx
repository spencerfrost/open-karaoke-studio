import React, { useState, useEffect } from "react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Search, Loader2 } from "lucide-react";

export interface SearchFormData {
  artist: string;
  title: string;
  album: string;
}

interface SearchFormProps {
  initialValues?: Partial<SearchFormData>;
  onSearch: (query: SearchFormData) => void;
  isLoading?: boolean;
  autoFocus?: boolean;
  submitButtonText?: string;
  layout?: "horizontal" | "vertical";
  className?: string;
  // Validation
  requireArtist?: boolean;
  requireTitle?: boolean;
  // Events
  onFieldChange?: (field: keyof SearchFormData, value: string) => void;
  onKeyPress?: (e: React.KeyboardEvent) => void;
}

export const SearchForm: React.FC<SearchFormProps> = ({
  initialValues = {},
  onSearch,
  isLoading = false,
  autoFocus = true,
  submitButtonText = "Search",
  layout = "vertical",
  className = "",
  requireArtist = true,
  requireTitle = true,
  onFieldChange,
  onKeyPress,
}) => {
  const [formData, setFormData] = useState<SearchFormData>({
    artist: initialValues.artist || "",
    title: initialValues.title || "",
    album: initialValues.album || "",
  });

  // Update form when initialValues change
  useEffect(() => {
    setFormData({
      artist: initialValues.artist || "",
      title: initialValues.title || "",
      album: initialValues.album || "",
    });
  }, [initialValues]);

  const handleFieldChange = (field: keyof SearchFormData, value: string) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    onFieldChange?.(field, value);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (isLoading) return;

    // Trim all values
    const trimmedData = Object.fromEntries(
      Object.entries(formData).map(([key, value]) => [key, value.trim()])
    ) as SearchFormData;

    onSearch(trimmedData);
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    onKeyPress?.(e);
    if (e.key === "Enter" && !e.shiftKey) {
      handleSubmit(e);
    }
  };

  const isValid = () => {
    if (requireTitle && !formData.title.trim()) return false;
    if (requireArtist && !formData.artist.trim()) return false;
    return true;
  };

  const gridClass =
    layout === "horizontal"
      ? "grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"
      : "space-y-4";

  const fieldClass =
    layout === "horizontal"
      ? "space-y-2"
      : "grid grid-cols-4 items-center gap-4";

  const labelClass = layout === "horizontal" ? "" : "text-right";

  const inputClass = layout === "horizontal" ? "w-full" : "col-span-3";

  return (
    <form onSubmit={handleSubmit} className={`${className}`}>
      <div className={gridClass}>
        {/* Title Field */}
        <div className={fieldClass}>
          <Label htmlFor="search-title" className={labelClass}>
            Title {requireTitle && "*"}
          </Label>
          <Input
            id="search-title"
            value={formData.title}
            onChange={(e) => handleFieldChange("title", e.target.value)}
            onKeyPress={handleKeyPress}
            className={inputClass}
            placeholder="Song title"
            required={requireTitle}
            autoFocus={autoFocus}
          />
        </div>

        {/* Artist Field */}
        <div className={fieldClass}>
          <Label htmlFor="search-artist" className={labelClass}>
            Artist {requireArtist && "*"}
          </Label>
          <Input
            id="search-artist"
            value={formData.artist}
            onChange={(e) => handleFieldChange("artist", e.target.value)}
            onKeyPress={handleKeyPress}
            className={inputClass}
            placeholder="Artist name"
            required={requireArtist}
          />
        </div>

        {/* Album Field */}
        <div className={fieldClass}>
          <Label htmlFor="search-album" className={labelClass}>
            Album
          </Label>
          <Input
            id="search-album"
            value={formData.album}
            onChange={(e) => handleFieldChange("album", e.target.value)}
            onKeyPress={handleKeyPress}
            className={inputClass}
            placeholder="Album name (optional)"
          />
        </div>
      </div>

      {/* Submit Button */}
      <div
        className={`mt-6 ${layout === "horizontal" ? "text-left" : "text-right"}`}
      >
        <Button
          type="submit"
          disabled={isLoading || !isValid()}
          className="flex items-center gap-2"
        >
          {isLoading ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Searching...
            </>
          ) : (
            <>
              <Search className="h-4 w-4" />
              {submitButtonText}
            </>
          )}
        </Button>
      </div>
    </form>
  );
};
