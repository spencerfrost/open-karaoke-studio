import React, { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { toast } from "sonner"; // For submission feedback

import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
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
import FileUpload from "../components/upload/FileUpload"; // The refactored FileUpload component
import YouTubeImporter from "../components/upload/YouTubeImporter";
import AppLayout from "../components/layout/AppLayout";
import {
  uploadAndProcessAudio,
  processYouTubeVideo,
} from "../services/uploadService";
import ProcessingQueue from "@/components/upload/ProcessingQueue";

// Define Zod schema for the File Upload form
const MAX_FILE_SIZE = 150 * 1024 * 1024; // 150MB (example)

const fileUploadFormSchema = z.object({
  audioFile: z
    .instanceof(File, { message: "Please select an audio file." })
    .refine(
      (file) => file.size <= MAX_FILE_SIZE,
      `Max file size is ${MAX_FILE_SIZE / (1024 * 1024)}MB.`
    )
    .optional()
    .nullable(),
  // Add other potential form fields for the upload tab here if needed
});

type FileUploadFormValues = z.infer<typeof fileUploadFormSchema>;

// --- Component Starts ---

const AddSongPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState("upload");

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
        `${fileToProcess.name} uploaded successfully and processing started!`
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

  // Handle YouTube import (remains unchanged)
  const handleYouTubeImport = async (
    url: string,
    title?: string,
    artist?: string
  ) => {
    // Consider adding loading/error state for YouTube import as well
    console.log(`Importing YouTube URL: ${url}`);
    try {
      const response = await processYouTubeVideo(url, { title, artist });
      if (response.error) {
        console.error("Error processing YouTube URL:", response.error);
        toast.error(`YouTube processing failed: ${response.error}`);
        return;
      }
      console.log("YouTube processing initiated:", response.data);
      toast.success(`YouTube video processing started for ${url}`);
    } catch (error) {
      console.error("YouTube processing error:", error);
      toast.error(
        `YouTube processing failed: ${
          error instanceof Error ? error.message : "Unknown error"
        }`
      );
    }
  };

  return (
    <AppLayout>
      <div>
        {/* Use Tailwind classes based on theme variables */}
        <h1 className="text-2xl font-semibold mb-6 text-secondary">
          {" "}
          {/* Assuming orangePeel maps to secondary */}
          Add New Songs
        </h1>

        <Tabs
          defaultValue="upload"
          value={activeTab}
          onValueChange={setActiveTab}
          className="mb-6"
        >
          {/* Style Tabs using Tailwind and data attributes */}
          <TabsList className="mb-4 p-1 rounded-lg bg-card/80 inline-flex">
            <TabsTrigger
              value="upload"
              className="px-4 py-2 rounded-md text-muted-foreground data-[state=active]:bg-primary data-[state=active]:text-primary-foreground transition-colors duration-150"
            >
              Upload File
            </TabsTrigger>
            <TabsTrigger
              value="youtube"
              className="px-4 py-2 rounded-md text-muted-foreground data-[state=active]:bg-primary data-[state=active]:text-primary-foreground transition-colors duration-150"
            >
              YouTube
            </TabsTrigger>
          </TabsList>

          {/* --- Upload Tab Content --- */}
          <TabsContent value="upload" className="mt-0">
            <Form {...form}>
              {/* Use the specific onSubmit handler for this form */}
              <form
                onSubmit={form.handleSubmit(onSubmitUpload)}
                className="space-y-6"
              >
                {/* File Upload Field using FormField */}
                <FormField
                  control={form.control}
                  name="audioFile" // Must match schema
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel className="text-foreground">
                        Audio File
                      </FormLabel>
                      <FormControl>
                        {/* Pass react-hook-form field props */}
                        <FileUpload
                          value={field.value}
                          onChange={field.onChange}
                          accept="audio/*" // Specify types
                          maxSize={MAX_FILE_SIZE} // Pass max size
                        />
                      </FormControl>
                      <FormDescription>
                        Select or drag and drop your audio file here.
                      </FormDescription>
                      {/* FormMessage displays Zod validation errors */}
                      <FormMessage />
                    </FormItem>
                  )}
                />

                {/* Display general submission errors for the upload form */}
                {uploadSubmissionError && (
                  <Alert variant="destructive">
                    <AlertDescription>{uploadSubmissionError}</AlertDescription>
                  </Alert>
                )}

                {/* Submit Button for the upload form */}
                <Button
                  type="submit"
                  disabled={isSubmittingUpload}
                  className="w-full sm:w-auto"
                >
                  {isSubmittingUpload ? "Processing..." : "Upload and Process"}
                </Button>
              </form>
            </Form>
          </TabsContent>

          {/* --- YouTube Tab Content (Unchanged) --- */}
          <TabsContent value="youtube" className="mt-0">
            <YouTubeImporter onYouTubeImport={handleYouTubeImport} />
          </TabsContent>
        </Tabs>

        {/* --- Processing Queue Section --- */}
        <div className="mt-8">
          <h2 className="text-xl font-semibold mb-3 text-secondary">
            {" "}
            {/* Assuming orangePeel maps to secondary */}
            Processing Queue
          </h2>

          {/* Processing Queue component would go here */}
          <ProcessingQueue />
        </div>
      </div>
    </AppLayout>
  );
};

export default AddSongPage;
