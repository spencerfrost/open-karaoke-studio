"use client";

import { Button } from "@/components/ui/button";
import { CloudUpload, Paperclip } from "lucide-react";
import React, { useState } from "react";
import * as z from "zod";
import {
  FileInput,
  FileUploader,
  FileUploaderContent,
  FileUploaderItem,
} from "./ui/file-uploader";
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "./ui/form";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { toast } from "sonner";

import { uploadFile } from "@/hooks/useApi";

const formSchema = z.object({
  // We might still want a string field for a description or related info
  songDescription: z.string().optional(),
});

const FileUpload: React.FC = () => {
  const [files, setFiles] = useState<File[] | null>([]); // Initialize as empty array

  const dropZoneConfig = {
    maxFiles: 5,
    maxSize: 1024 * 1024 * 4,
    multiple: true,
  };

  const form = useForm<z.infer<typeof formSchema>>({
    resolver: zodResolver(formSchema),
  });

  function onSubmit(values: z.infer<typeof formSchema>) {
    try {
      console.log("Form Values:", values);
      console.log("Selected Files:", files); // Access the files state directly

      if (files && files.length > 0) {
        toast(
          <pre className="mt-2 w-[340px] rounded-md bg-slate-950 p-4">
            <code className="text-white">
              {JSON.stringify({ ...values, files: files.map((f) => f.name) }, null, 2)}
            </code>
          </pre>
        );
        // Here you would typically handle the file upload logic (e.g., sending to a server)
        uploadFile("/process", files[0]); // Replace with your actual upload logic

      } else {
        toast.warning("Please select at least one file.");
      }
    } catch (error) {
      console.error("Form submission error", error);
      toast.error("Failed to submit the form. Please try again.");
    }
  }

  return (
    <div>
      <label
        htmlFor="audio-file"
        className="block text-sm font-medium text-gray-700"
      >
        Audio File:
      </label>
      <div className="mt-1 flex rounded-md shadow-sm">
        <Form {...form}>
          <form
            onSubmit={form.handleSubmit(onSubmit)}
            className="space-y-8 max-w-3xl mx-auto py-10"
          >
            <FormField
              control={form.control}
              name="songDescription" // Changed name to reflect its purpose
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Select File</FormLabel>
                  <FormControl>
                    <FileUploader
                      value={files}
                      onValueChange={setFiles}
                      dropzoneOptions={dropZoneConfig}
                      className="relative bg-background rounded-lg p-2"
                    >
                      <FileInput
                        id="fileInput"
                        className="outline-dashed outline-1 outline-slate-500"
                      >
                        <div className="flex items-center justify-center flex-col p-8 w-full ">
                          <CloudUpload className="text-gray-500 w-10 h-10" />
                          <p className="mb-1 text-sm text-gray-500 dark:text-gray-400">
                            <span className="font-semibold">
                              Click to upload
                            </span>{' '}
                            or drag and drop
                          </p>
                          <p className="text-xs text-gray-500 dark:text-gray-400">
                            SVG, PNG, JPG or GIF
                          </p>
                        </div>
                      </FileInput>
                      <FileUploaderContent>
                        {files &&
                          files.length > 0 &&
                          files.map((file, i) => (
                            <FileUploaderItem key={i} index={i}>
                              <Paperclip className="h-4 w-4 stroke-current" />
                              <span>{file.name}</span>
                            </FileUploaderItem>
                          ))}
                      </FileUploaderContent>
                    </FileUploader>
                  </FormControl>
                  <FormDescription>Select a file to upload.</FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />
            <Button type="submit">Submit</Button>
          </form>
        </Form>
      </div>
    </div>
  );
};

export default FileUpload;