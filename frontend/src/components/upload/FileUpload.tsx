import React, { useState, useCallback, useId, useEffect } from "react"; // Added useEffect
import { Upload, X, Paperclip } from "lucide-react";
import { isAudioFile } from "../../utils/validators";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  FileUploader,
  FileInput,
  FileUploaderContent,
  FileUploaderItem,
} from "@/components/ui/file-uploader";

// Interface for props provided by FormField render prop (simplified)
interface FileUploadFieldProps {
  value?: File | null; // Value from react-hook-form (single File or null/undefined)
  onChange: (file: File | null) => void; // Callback to update react-hook-form state
  accept?: string;
  maxSize?: number;
}

// Helper (keep as is or refine)
const generateAcceptObject = (
  acceptString?: string,
): { [key: string]: string[] } | undefined => {
  // ... (implementation from previous step) ...
  if (!acceptString) return undefined;
  try {
    if (acceptString.includes("/") || acceptString.includes("*")) {
      const types = acceptString.split(",").map((t) => t.trim());
      const acceptObj: { [key: string]: string[] } = {};
      types.forEach((type) => {
        acceptObj[type] = [];
      });
      return acceptObj;
    }
    const extensions = acceptString.split(",").map((ext) => ext.trim());
    return { "application/octet-stream": extensions };
  } catch (error) {
    console.error("Error parsing accept string:", error);
    return undefined;
  }
};

// Component receives props compatible with react-hook-form's field object
const FileUpload: React.FC<FileUploadFieldProps> = ({
  value: rhfValue, // Rename prop to avoid conflict with internal state name
  onChange: rhfOnChange, // Rename prop
  accept = "audio/*",
  maxSize = 100 * 1024 * 1024,
}) => {
  // Internal state for the FileUploader component, which expects File[] | null
  const [internalFiles, setInternalFiles] = useState<File[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const fileInputId = useId();

  // Sync internal state <-> react-hook-form state
  useEffect(() => {
    // Update internal state when react-hook-form value changes externally
    // (e.g., form reset)
    if (rhfValue && !internalFiles?.some((f) => f === rhfValue)) {
      setInternalFiles([rhfValue]);
    } else if (!rhfValue && internalFiles) {
      setInternalFiles(null);
    }
    // Intentionally simplified dependency array to only react on RHF value change
    // Avoids potential loops if internalFiles was included.
  }, [rhfValue]); // eslint-disable-line react-hooks/exhaustive-deps

  const dropZoneConfig = {
    maxFiles: 1,
    maxSize: maxSize,
    multiple: false,
    accept: generateAcceptObject(accept),
  };

  // This handler is called by the FileUploader extension component
  const handleInternalValueChange = useCallback(
    (acceptedValue: File[] | null) => {
      setError(null); // Clear local errors on new selection attempt

      const file = acceptedValue?.[0] ?? null; // Get the single file or null

      if (file) {
        // Optional: Perform extra checks NOT handled by dropzone (like isAudioFile)
        if (!isAudioFile(file)) {
          console.warn(
            "File passed dropzone but failed isAudioFile check:",
            file.name,
          );
          setError("Invalid file type. Please select a valid audio file.");
          setInternalFiles(null); // Clear internal state
          rhfOnChange(null); // Update RHF state to null
          return;
        }
        // File is valid
        setInternalFiles(acceptedValue); // Update internal state (File[])
        rhfOnChange(file); // Update RHF state (File | null)
      } else {
        // No file selected or cleared by the component
        setInternalFiles(null); // Update internal state
        rhfOnChange(null); // Update RHF state
      }
    },
    [rhfOnChange], // Dependency: react-hook-form's onChange
  );

  // Handler for the clear button
  const clearFile = useCallback(() => {
    setError(null);
    setInternalFiles(null); // Clear internal state
    rhfOnChange(null); // Update RHF state
  }, [rhfOnChange]);

  const triggerFileInput = () => {
    const inputElement = document.getElementById(fileInputId);
    inputElement?.click();
  };

  // Use the internal state for display logic
  const displayFile = internalFiles?.[0];

  return (
    <div className="w-full space-y-2">
      {/* FileUploader now controlled by internalFiles, but updates RHF via handleInternalValueChange */}
      <FileUploader
        value={internalFiles}
        onValueChange={handleInternalValueChange}
        dropzoneOptions={dropZoneConfig}
        className="relative bg-card text-card-foreground border border-border rounded-lg p-2 data-[state=dragging]:border-primary data-[state=dragging]:ring-2 data-[state=dragging]:ring-offset-2 data-[state=dragging]:ring-primary data-[state=dragging]:ring-offset-card"
      >
        <FileInput
          id={fileInputId}
          className="outline-dashed outline-1 outline-border hover:outline-primary data-[state=dragging]:bg-primary/10 data-[state=dragging]:outline-primary"
        >
          {/* ... Input display unchanged ... */}
          <div className="flex items-center justify-center flex-col py-6 text-center">
            <Upload className="w-10 h-10 mb-2 text-primary" />
            <p className="mb-1 text-sm text-muted-foreground">
              <button
                type="button"
                className="font-semibold text-primary cursor-pointer underline-offset-2 hover:underline focus:outline-none focus:ring-1 focus:ring-ring rounded"
                onClick={(e) => {
                  e.stopPropagation();
                  triggerFileInput();
                }}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    triggerFileInput();
                  }
                }}
              >
                Click to upload
              </button>
              <span className="ml-1">or drag and drop</span>
            </p>
            <p className="text-xs text-muted-foreground/80">
              Audio file (Max: {Math.round(maxSize / (1024 * 1024))}MB)
            </p>
          </div>
        </FileInput>

        {/* Display logic uses displayFile (derived from internalFiles) */}
        {displayFile && (
          <FileUploaderContent className="mt-2">
            <FileUploaderItem
              key={displayFile.name}
              index={0}
              className="p-2 bg-muted/50 rounded flex items-center justify-between space-x-2"
              aria-label={`Selected file ${displayFile.name}`}
            >
              {/* ... File item display unchanged, but uses clearFile ... */}
              <div className="flex items-center gap-2 flex-1 min-w-0">
                <Paperclip className="h-5 w-5 stroke-current flex-shrink-0" />
                <span className="text-sm font-medium text-card-foreground truncate">
                  {displayFile.name}
                </span>
              </div>
              <div className="flex items-center gap-2 flex-shrink-0">
                <span className="text-xs text-muted-foreground">
                  ({(displayFile.size / (1024 * 1024)).toFixed(2)} MB)
                </span>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-6 w-6 p-0 text-destructive hover:bg-destructive/10"
                  onClick={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    clearFile();
                  }} // Uses new clearFile
                  aria-label="Remove file"
                >
                  <X size={16} />
                </Button>
              </div>
            </FileUploaderItem>
          </FileUploaderContent>
        )}
      </FileUploader>

      {/* Local error display (for non-form validation errors) */}
      {error && (
        <Alert variant="destructive" className="mt-2">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
      {/* Note: Form validation errors should be displayed via FormMessage in AddSong */}
    </div>
  );
};

export default FileUpload;
