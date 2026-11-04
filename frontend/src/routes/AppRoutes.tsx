import React from "react";
import { Routes, Route, Navigate } from "react-router-dom";

import LibraryPage from "../pages/Library";
import AddSongPage from "../pages/AddSong";
import SettingsPage from "../pages/Settings";
import StagePage from "../pages/Stage";
import PerformanceControlsPage from "../pages/PerformanceControlsPage";
import Entry from "../pages/Entry";
import AdminThreeTrackComparePage from "../pages/AdminThreeTrackComparePage";
import AdminLayout from "../features/admin/AdminLayout";
import AdminIndex from "../features/admin/AdminIndex";
import AdminJobsPage from "../features/admin/AdminJobsPage";
import AdminUsersPage from "../features/admin/AdminUsersPage";
import AdminAcoustIdPage from "../features/admin/AdminAcoustIdPage";
import AdminDiskCheckPage from "../features/admin/AdminDiskCheckPage";
import AdminDuplicatesPage from "../features/admin/AdminDuplicatesPage";
import AdminFailedSongsPage from "../features/admin/AdminFailedSongsPage";
import AdminLyricsFeedbackPage from "../features/admin/AdminLyricsFeedbackPage";
import AdminLyricsReportsPage from "../features/admin/AdminLyricsReportsPage";
import AdminMetadataPage from "../features/admin/AdminMetadataPage";
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
      <Route path="/add/*" element={<AddSongPage />} />

      {/* Any account, host or not. A session guest has no settings. */}
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
        <Route path="/admin" element={<AdminLayout />}>
          <Route index element={<AdminIndex />} />
          <Route path="lyrics-reports" element={<AdminLyricsReportsPage />} />
          <Route path="lyrics-feedback" element={<AdminLyricsFeedbackPage />} />
          <Route path="acoustid" element={<AdminAcoustIdPage />} />
          <Route path="metadata" element={<AdminMetadataPage />} />
          <Route path="failed" element={<AdminFailedSongsPage />} />
          <Route path="duplicates" element={<AdminDuplicatesPage />} />
          <Route path="disk" element={<AdminDiskCheckPage />} />
          <Route path="jobs" element={<AdminJobsPage />} />
          <Route
            path="alignment"
            element={<Navigate to="/admin/jobs" replace />}
          />
          <Route path="compare" element={<AdminThreeTrackComparePage />} />
          <Route path="users" element={<AdminUsersPage />} />
          <Route
            path="compare-three-track"
            element={<Navigate to="/admin/compare" replace />}
          />
          <Route path="*" element={<Navigate to="/admin" replace />} />
        </Route>
      </Route>
    </Route>

    {/* Fallback route */}
    <Route path="*" element={<Navigate to="/" replace />} />
  </Routes>
);

export default AppRoutes;
