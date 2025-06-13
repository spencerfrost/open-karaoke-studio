import React from "react";
import YouTubeSearch from "../components/upload/YouTubeSearch";
import AppLayout from "../components/layout/AppLayout";
import JobsQueue from "@/components/upload/JobsQueue";

const AddSongPage: React.FC = () => {
  return (
    <AppLayout>
      <div className="p-4 md:p-6 space-y-6 container mx-auto">
        <JobsQueue />
        <YouTubeSearch />
      </div>
    </AppLayout>
  );
};

export default AddSongPage;
