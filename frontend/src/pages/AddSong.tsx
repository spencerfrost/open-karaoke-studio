import React, { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
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
import FileUpload from "../components/upload/FileUpload";
import YouTubeSearch from "../components/upload/YouTubeSearch";
import AppLayout from "../components/layout/AppLayout";
import { useUploadAndProcessAudio } from "../services/uploadService";
import ProcessingQueue from "@/components/upload/ProcessingQueue";

// Define Zod schema for the File Upload form
const MAX_FILE_SIZE = 150 * 1024 * 1024; // 150MB

const fileUploadFormSchema = z.object({
  audioFile: z
    .instanceof(File, { message: "Please select an audio file." })
    .refine(
      (file) => file.size <= MAX_FILE_SIZE,
      `Max file size is ${MAX_FILE_SIZE / (1024 * 1024)}MB.`
    )
    .optional()
    .nullable(),
});

type FileUploadFormValues = z.infer<typeof fileUploadFormSchema>;

// --- Component Starts ---

const AddSongPage: React.FC = () => {
  // State for File Upload form submission
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

  // Use React Query mutation for upload
  const uploadMutation = useUploadAndProcessAudio({
    onSuccess: (_, variables) => {
      console.log(variables);
      toast.success(
        `${variables.file.name} uploaded successfully and processing started!`
      );
      form.reset();
      setUploadSubmissionError(null);
    },
    onError: (error) => {
      const errorMsg =
        error instanceof Error ? error.message : "Unknown upload error.";
      setUploadSubmissionError(errorMsg);
      toast.error(`Upload failed: ${errorMsg}`);
    },
  });

  // onSubmit handler for the File Upload form
  const onSubmitUpload = (values: FileUploadFormValues) => {
    setUploadSubmissionError(null);
    const fileToProcess = values.audioFile;

    if (!fileToProcess) {
      setUploadSubmissionError("No audio file selected.");
      form.setError("audioFile", {
        type: "manual",
        message: "Please select a file before submitting.",
      });
      toast.error("Please select a file before submitting.");
      return;
    }

    uploadMutation.mutate({ file: fileToProcess });
  };

  return (
    <AppLayout>
      <div className="p-4 md:p-6 space-y-6 container mx-auto">
        <ProcessingQueue />
        <YouTubeSearch />

        <Card className="bg-card/80">
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
                          className="bg-card/50"
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
                  disabled={uploadMutation.status === "pending"}
                  className="w-full sm:w-auto"
                >
                  {uploadMutation.status === "pending"
                    ? "Processing..."
                    : "Upload and Process"}
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
