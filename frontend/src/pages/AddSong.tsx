import React from "react";
import { useSearchParams } from "react-router-dom";
import AppLayout from "../components/layout/AppLayout";
import { JobsQueue } from "@/features/jobs";
import { SongSearchContainer } from "@/features/songs/components/shared/SongSearchContainer";
import SessionInfoDisplay from "@/components/session/SessionInfoDisplay";

const AddSongPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const initialQuery = searchParams.get("q") || "";

  return (
    <AppLayout>
      <SessionInfoDisplay variant="code" colorScheme="page" trigger="hover" visibility="host-only" className="absolute top-2 right-3 z-30" />
      <div className="md:p-6 space-y-6 container mx-auto">
        <JobsQueue />
        <SongSearchContainer initialQuery={initialQuery} />
      </div>
    </AppLayout>
  );
};

export default AddSongPage;
