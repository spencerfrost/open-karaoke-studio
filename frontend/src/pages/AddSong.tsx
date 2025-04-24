import React, { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { toast } from "sonner";
import { Upload } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import FileUpload from "../components/upload/FileUpload";
import YouTubeSearch from "../components/upload/YouTubeSearch";
import AppLayout from "../components/layout/AppLayout";
import { uploadAndProcessAudio } from "../services/uploadService";
import ProcessingQueue from "@/components/upload/ProcessingQueue";

// Define Zod schema for the File Upload form
const MAX_FILE_SIZE = 150 * 1024 * 1024; // 150MB

const fileUploadFormSchema = z.object({
  audioFile: z
    .instanceof(File, { message: "Please select an audio file." })
    .refine(
      (file) => file.size <= MAX_FILE_SIZE,
      `Max file size is ${MAX_FILE_SIZE / (1024 * 1024)}MB.`,
    )
    .optional()
    .nullable(),
});

type FileUploadFormValues = z.infer<typeof fileUploadFormSchema>;

// --- Component Starts ---

const AddSongPage: React.FC = () => {
  // State for File Upload form submission
  const [isSubmittingUpload, setIsSubmittingUpload] = useState(false);
  const [uploadSubmissionError, setUploadSubmissionError] = useState<
    string | null
  >(null);

  // Initialize react-hook-form for the File Upload tab
  const form = useForm<FileUploadFormValues>({
    resolver: zodResolver(fileUploadFormSchema),
    defaultValues: {
      audioFile: null,
    },
  });

  // onSubmit handler for the File Upload form
  const onSubmitUpload = async (values: FileUploadFormValues) => {
    setIsSubmittingUpload(true);
    setUploadSubmissionError(null);
    const fileToProcess = values.audioFile;

    if (!fileToProcess) {
      setUploadSubmissionError("No audio file selected.");
      setIsSubmittingUpload(false);
      form.setError("audioFile", {
        type: "manual",
        message: "Please select a file before submitting.",
      });
      toast.error("Please select a file before submitting.");
      return;
    }

    console.log("Attempting to upload and process file:", fileToProcess.name);
    try {
      // Call the service function (previously in handleFileUpload)
      const response = await uploadAndProcessAudio(fileToProcess);

      if (response.error) {
        console.error("Error uploading file:", response.error);
        const errorMsg =
          typeof response.error === "string"
            ? response.error
            : "Unknown upload error.";
        setUploadSubmissionError(errorMsg);
        toast.error(`Upload failed: ${errorMsg}`);
        return; // Stop execution on handled error
      }

      // Handle successful upload
      console.log("File uploaded successfully:", response.data);
      toast.success(
        `${fileToProcess.name} uploaded successfully and processing started!`,
      );
      form.reset(); // Reset form fields on success
    } catch (error) {
      console.error("Upload submission error:", error);
      const errorMsg =
        error instanceof Error
          ? error.message
          : "An unexpected error occurred during upload.";
      setUploadSubmissionError(errorMsg);
      toast.error(`Upload failed: ${errorMsg}`);
    } finally {
      setIsSubmittingUpload(false);
    }
  };

  // Handle YouTube download start
  const handleYouTubeDownloadStart = (videoId: string, title: string) => {
    toast.info(`Started processing "${title}"`);
    // Additional code could be added here to update UI or track downloads
  };

  return (
    <AppLayout>
      <div className="p-4 md:p-6 space-y-6">
        <ProcessingQueue />
        <YouTubeSearch onDownloadStart={handleYouTubeDownloadStart} />

        {/* Upload Alternative */}
        <Card>
          <CardHeader>
            <CardTitle>Upload File</CardTitle>
            <CardDescription>Or upload your own audio files</CardDescription>
          </CardHeader>

          <CardContent>
            <Form {...form}>
              <form
                onSubmit={form.handleSubmit(onSubmitUpload)}
                className="space-y-6"
              >
                <FormField
                  control={form.control}
                  name="audioFile"
                  render={({ field }) => (
                    <FormItem>
                      <FormControl>
                        <FileUpload
                          value={field.value}
                          onChange={field.onChange}
                          accept="audio/*"
                          maxSize={MAX_FILE_SIZE}
                        />
                      </FormControl>
                      <FormDescription>
                        Select or drag and drop your audio file here.
                      </FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                {uploadSubmissionError && (
                  <Alert variant="destructive">
                    <AlertDescription>{uploadSubmissionError}</AlertDescription>
                  </Alert>
                )}

                <Button
                  type="submit"
                  disabled={isSubmittingUpload}
                  className="w-full sm:w-auto"
                >
                  {isSubmittingUpload ? "Processing..." : "Upload and Process"}
                </Button>
              </form>
            </Form>
          </CardContent>
        </Card>
      </div>
    </AppLayout>
  );
};

export default AddSongPage;
