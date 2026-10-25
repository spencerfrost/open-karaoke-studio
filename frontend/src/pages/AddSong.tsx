import React from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import AppLayout from "../components/layout/AppLayout";
import SessionInfoDisplay from "@/components/session/SessionInfoDisplay";
import { AddSongFlow } from "@/features/songs/components/add-song/AddSongFlow";
import type { AddFlowStep } from "@/hooks/useAddFlowNavigation";

/**
 * The add-song flow on a phone or desktop: `/add?q=…`, `/add/artist/:browseId`
 * and `/add/album/:browseId`. One route for all three, so the flow stays
 * mounted as it moves between them.
 */
const useRouteStep = (): AddFlowStep => {
  const { "*": rest = "" } = useParams();
  const { search, state } = useLocation();
  const backLabel = (state as { backLabel?: string } | null)?.backLabel;
  const [kind, browseId] = rest.split("/");

  if (kind === "artist" && browseId) return { kind, browseId, backLabel };
  if (kind === "album" && browseId) return { kind, browseId, backLabel };

  const params = new URLSearchParams(search);
  return {
    kind: "search",
    query: params.get("q") ?? undefined,
    findArtist: params.get("findArtist") === "1",
    openTopArtist: params.get("openTopArtist") === "1",
  };
};

const AddSongPage: React.FC = () => {
  const step = useRouteStep();
  const navigate = useNavigate();

  return (
    <AppLayout contentClassName="pt-2 sm:pt-4">
      <SessionInfoDisplay className="absolute top-2 right-3 z-30" />
      <AddSongFlow step={step} onExit={() => navigate("/")} />
    </AppLayout>
  );
};

export default AddSongPage;
