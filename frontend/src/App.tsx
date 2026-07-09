import React from "react";
import {
  BrowserRouter as Router,
  Routes,
  Route,
  Navigate,
} from "react-router-dom";

import LibraryPage from "./pages/Library";
import AddSongPage from "./pages/AddSong";
import SettingsPage from "./pages/Settings";
import StagePage from "./pages/Stage";
import PerformanceControlsPage from "./pages/PerformanceControlsPage";
import JoinSessionPage from "./pages/JoinSessionPage";
import QRJoinPage from "./pages/QRJoinPage";
import HostDashboard from "./pages/HostDashboard";
import AdminPanel from "./pages/AdminPanel";
import AdminThreeTrackComparePage from "./pages/AdminThreeTrackComparePage";
import { SessionProvider } from "./contexts/SessionContext";
import SessionGuard from "./components/SessionGuard";
import HostGuard from "./components/HostGuard";
import AdminGuard from "./components/AdminGuard";
import { Toaster } from "./components/ui/sonner";
import { MiniPlayer } from "./components/player/MiniPlayer";
import { useJobsSync } from "./hooks/useJobsSync";
import { PWAUpdatePrompt } from "./components/PWAUpdatePrompt";

const App: React.FC = () => {
  useJobsSync(); // Sync jobs to processing indicators store

  return (
    <>
      <Toaster />
      <PWAUpdatePrompt />
      <Router>
        <SessionProvider>
          <Routes>
            {/* Session entry point - public routes */}
            <Route path="/join" element={<JoinSessionPage />} />
            <Route path="/join/:code" element={<QRJoinPage />} />

            {/* Session-required routes */}
            <Route
              path="/"
              element={
                <SessionGuard>
                  <LibraryPage />
                </SessionGuard>
              }
            />
            <Route
              path="/add"
              element={
                <SessionGuard>
                  <AddSongPage />
                </SessionGuard>
              }
            />
            <Route
              path="/settings"
              element={
                <SessionGuard requireSession={false}>
                  <SettingsPage />
                </SessionGuard>
              }
            />
            <Route
              path="/stage"
              element={
                <SessionGuard deviceType="stage" redirectTo="/stage">
                  <StagePage />
                </SessionGuard>
              }
            />
            <Route
              path="/controls"
              element={
                <SessionGuard deviceType="performer" redirectTo="/controls">
                  <PerformanceControlsPage />
                </SessionGuard>
              }
            />

            {/* Host dashboard */}
            <Route
              path="/host"
              element={
                <HostGuard>
                  <HostDashboard />
                </HostGuard>
              }
            />

            {/* Admin panel */}
            <Route
              path="/admin"
              element={
                <AdminGuard>
                  <AdminPanel />
                </AdminGuard>
              }
            />
            <Route
              path="/admin/compare-three-track"
              element={
                <AdminGuard>
                  <AdminThreeTrackComparePage />
                </AdminGuard>
              }
            />

            {/* Fallback route */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>

          {/* Mini-player renders outside routes, always available */}
          <MiniPlayer />
        </SessionProvider>
      </Router>
    </>
  );
};

export default App;
