import React from "react";
import AppLayout from "../components/layout/AppLayout";
import JobsQueue from "@/components/JobsQueue";
import { SongSearchContainer } from "@/components/add-song/shared";

const AddSongPage: React.FC = () => {
  return (
    <AppLayout>
      <div className="p-4 md:p-6 space-y-6 container mx-auto">
        <JobsQueue />
        <SongSearchContainer />
      </div>
    </AppLayout>
  );
};

export default AddSongPage;
