import React from "react";
import YouTubeSearch from "../components/add/youtube/YouTubeSearch";
import AppLayout from "../components/layout/AppLayout";
import JobsQueue from "@/components/add/JobsQueue";
import { YouTubeMusicSearch } from "../components/add/YouTubeMusicSearch";

const AddSongPage: React.FC = () => {
  return (
    <AppLayout>
      <div className="p-4 md:p-6 space-y-6 container mx-auto">
        <JobsQueue />
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <YouTubeSearch />
          <YouTubeMusicSearch />
        </div>
      </div>
    </AppLayout>
  );
};

export default AddSongPage;
