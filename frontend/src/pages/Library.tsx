import React from "react";
import { useSearchParams } from "react-router-dom";
import AppLayout from "@/components/layout/AppLayout";
import { LibraryScreen } from "@/features/library";
import SessionInfoDisplay from "@/components/session/SessionInfoDisplay";

/**
 * The library as a route. The browsing itself lives in `LibraryScreen`, which
 * the stage renders too — this page only supplies the chrome and the URL state.
 */
const LibraryPage: React.FC = () => {
  const [searchParams] = useSearchParams();

  return (
    <AppLayout>
      <SessionInfoDisplay
        variant="qr"
        colorScheme="page"
        trigger="hover"
        visibility="host-only"
        className="absolute top-2 right-3 z-30"
      />
      <LibraryScreen expandArtist={searchParams.get("expandArtist")} />
    </AppLayout>
  );
};

export default LibraryPage;
