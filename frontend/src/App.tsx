import React from "react";
import {
  BrowserRouter as Router,
  Routes,
  Route,
  Navigate,
} from "react-router-dom";

// Context providers
import { SongsProvider } from "./context/SongsContext";
import { QueueProvider } from "./context/QueueContext";
import { PlayerProvider } from "./context/PlayerContext";
import { SettingsProvider } from "./context/SettingsContext";

// Pages
import LibraryPage from "./pages/Library";
import AddSongPage from "./pages/AddSong";
import QueuePage from "./pages/Queue";
import SettingsPage from "./pages/Settings";
import PlayerPage from "./pages/Player";
import PerformanceControlsPage from "./pages/PerformanceControlsPage";

const App: React.FC = () => {
  return (
    <SettingsProvider>
      <SongsProvider>
        <QueueProvider>
          <PlayerProvider>
            <Router>
              <Routes>
                {/* Main app routes */}
                <Route path="/" element={<LibraryPage />} />
                <Route path="/add" element={<AddSongPage />} />
                <Route path="/queue" element={<QueuePage />} />
                <Route path="/settings" element={<SettingsPage />} />

                {/* Player routes */}
                <Route path="/player" element={<PlayerPage />} />
                <Route path="/player/:id" element={<PlayerPage />} />
                
                {/* Performance controls route - simplified to global */}
                <Route path="/player/controls" element={<PerformanceControlsPage />} />

                {/* Fallback route */}
                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
            </Router>
          </PlayerProvider>
        </QueueProvider>
      </SongsProvider>
    </SettingsProvider>
  );
};

export default App;
