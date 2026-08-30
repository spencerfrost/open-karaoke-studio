import React from "react";
import { Routes, Route, Navigate } from "react-router-dom";

import LibraryPage from "../pages/Library";
import AddSongPage from "../pages/AddSong";
import SettingsPage from "../pages/Settings";
import StagePage from "../pages/Stage";
import PerformanceControlsPage from "../pages/PerformanceControlsPage";
import Entry from "../pages/Entry";
import AdminPanel from "../pages/AdminPanel";
import AdminThreeTrackComparePage from "../pages/AdminThreeTrackComparePage";
import { RequireAccess, RequireCapability } from "./guards";

const AppRoutes: React.FC = () => (
  <Routes>
    {/* Session entry point - the app's one ungated screen. */}
    <Route path="/join" element={<Entry />} />
    <Route path="/join/:code" element={<Entry />} />

    {/* THE gate: an account, or a session. Nothing more specific. */}
    <Route element={<RequireAccess />}>
      {/* No further requirement. */}
      <Route path="/" element={<LibraryPage />} />
      <Route path="/add" element={<AddSongPage />} />

      {/* Any account - the account card is the point. */}
      <Route element={<RequireCapability account />}>
        <Route path="/settings" element={<SettingsPage />} />
      </Route>

      {/* Host account. No session required - this route creates one. */}
      <Route element={<RequireCapability host />}>
        <Route path="/stage" element={<StagePage />} />
      </Route>

      {/* A live session, on a performer's device. */}
      <Route element={<RequireCapability session device="performer" />}>
        <Route path="/controls" element={<PerformanceControlsPage />} />
      </Route>

      <Route element={<RequireCapability admin />}>
        <Route path="/admin" element={<AdminPanel />} />
        <Route
          path="/admin/compare-three-track"
          element={<AdminThreeTrackComparePage />}
        />
      </Route>
    </Route>

    {/* Fallback route */}
    <Route path="*" element={<Navigate to="/" replace />} />
  </Routes>
);

export default AppRoutes;
