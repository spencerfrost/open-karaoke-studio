import React from "react";
import {
  BrowserRouter as Router,
  Routes,
  Route,
  Navigate,
} from "react-router-dom";

import { SongsProvider } from "./context/SongsContext";
import { SettingsProvider } from "./context/SettingsContext";

import LibraryPage from "./pages/Library";
import AddSongPage from "./pages/AddSong";
import SettingsPage from "./pages/Settings";
import StagePage from "./pages/Stage";
import SongPlayerPage from "./pages/SongPlayer";
import PerformanceControlsPage from "./pages/PerformanceControlsPage";
import { Toaster } from "./components/ui/sonner";

const App: React.FC = () => {
  return (
    <SettingsProvider>
      <SongsProvider>
        <Toaster />
        <Router>
          <Routes>
            {/* Main app routes */}
            <Route path="/" element={<LibraryPage />} />
            <Route path="/add" element={<AddSongPage />} />
            <Route path="/settings" element={<SettingsPage />} />
            <Route path="/stage" element={<StagePage />} />
            <Route path="/player/:id" element={<SongPlayerPage />} />
            <Route path="/controls" element={<PerformanceControlsPage />} />

            {/* Fallback route */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Router>
      </SongsProvider>
    </SettingsProvider>
  );
};

export default App;
