import React from "react";
import AppLayout from "../components/layout/AppLayout";
import { JobsQueue } from "@/features/jobs";
import { SongSearchContainer } from "@/features/songs/components/shared/SongSearchContainer";

const AddSongPage: React.FC = () => {
  return (
    <AppLayout>
      <div className="md:p-6 space-y-6 container mx-auto">
        <JobsQueue />
        <SongSearchContainer />
      </div>
    </AppLayout>
  );
};

export default AddSongPage;
