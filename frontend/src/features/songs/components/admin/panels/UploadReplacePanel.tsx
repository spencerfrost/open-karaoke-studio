import React, { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { useAuthStore } from "@/stores/authStore";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { createLogger } from "@/lib/logger";
import FileUpload from "@/features/songs/components/upload/FileUpload";
import { uploadFile } from "@/hooks/api/useApi";
import type { ReplacePanelProps, ValidationResult } from "./types";

const logger = createLogger("component:UploadReplacePanel");

export const UploadReplacePanel: React.FC<ReplacePanelProps> = ({ song, onDone }) => {
  const { token } = useAuthStore();
  const [file, setFile] = useState<File | null>(null);
  const [validation, setValidation] = useState<ValidationResult | null>(null);
  const [isUploading, setIsUploading] = useState(false);

  const handleFileChange = (f: File | null) => {
    setFile(f);
    setValidation(null);
  };

  const validateMutation = useMutation({
    mutationFn: async (audioFile: File) => {
      const formData = new FormData();
      formData.append("audio_file", audioFile);
      const res = await fetch(`/api/songs/${song.id}/validate-upload-replacement`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      });
      if (!res.ok) throw new Error("Validation request failed");
      return res.json() as Promise<ValidationResult>;
    },
    onSuccess: (result) => setValidation(result),
    onError: (e: Error) => toast.error(e.message),
  });

  const handleUpload = async () => {
    if (!file) return;
    setIsUploading(true);
    try {
      await uploadFile(`songs/${song.id}/replace-upload`, file, {
        engine_type: "three_track",
      });
      toast.success("Upload started — full reprocessing queued");
      onDone();
    } catch (e) {
      logger.error("Upload failed", e);
      toast.error(e instanceof Error ? e.message : "Upload failed");
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="space-y-3">
      <FileUpload value={file} onChange={handleFileChange} />

      {file && !validation && (
        <Button
          size="sm"
          variant="outline"
          disabled={validateMutation.isPending}
          onClick={() => validateMutation.mutate(file)}
        >
          {validateMutation.isPending ? "Checking AcoustID..." : "Check AcoustID Match"}
        </Button>
      )}

      {validation && (
        <div
          className={`rounded border p-3 text-sm space-y-2 ${
            validation.validated
              ? "bg-green-500/10 border-green-500/30"
              : "bg-yellow-500/10 border-yellow-500/30"
          }`}
        >
          <p className={validation.validated ? "text-green-400" : "text-yellow-400"}>
            {validation.message}
          </p>
          {validation.acoustidStatus === "matched" && validation.title && (
            <p className="text-xs text-muted-foreground">
              Matched: <span className="text-foreground">{validation.title}</span>
              {" by "}
              <span className="text-foreground">{validation.artist}</span>
            </p>
          )}
          <div className="flex gap-2 pt-1">
            {validation.validated ? (
              <Button size="sm" disabled={isUploading} onClick={handleUpload}>
                {isUploading ? "Uploading..." : "Confirm & Process"}
              </Button>
            ) : (
              <p className="text-xs text-muted-foreground italic">
                Try a different file, or use MusicBrainz to set metadata manually.
              </p>
            )}
            <Button
              size="sm"
              variant="ghost"
              onClick={() => { setValidation(null); setFile(null); }}
            >
              Cancel
            </Button>
          </div>
        </div>
      )}
    </div>
  );
};
