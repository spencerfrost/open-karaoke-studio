import React from "react";
import { Navigate, useSearchParams } from "react-router-dom";
import AdminOverviewPage from "./AdminOverviewPage";

/** Where the old tabbed admin page's `?tab=` values live now. */
const OLD_TAB_ROUTES: Record<string, string> = {
  users: "users",
  acoustid: "acoustid",
  audit: "disk",
  "data-quality": "metadata",
  duplicates: "duplicates",
  alignment: "jobs",
  "lyrics-reports": "lyrics-reports",
};

/**
 * /admin itself: the overview. Old `/admin?tab=…` links go to their section.
 */
const AdminIndex: React.FC = () => {
  const [searchParams] = useSearchParams();
  const tab = searchParams.get("tab");
  const target = tab ? OLD_TAB_ROUTES[tab] : undefined;
  return target ? (
    <Navigate to={`/admin/${target}`} replace />
  ) : (
    <AdminOverviewPage />
  );
};

export default AdminIndex;
