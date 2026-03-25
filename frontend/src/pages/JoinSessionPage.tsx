import { useState } from "react";
import { useSessionStore } from "../stores/sessionStore";

export default function JoinSessionPage() {
  const [sessionCode, setSessionCode] = useState("");
  const [deviceType, setDeviceType] = useState<
    "stage" | "performer" | "controller"
  >("performer");
  const { joinSession, isConnecting, connectionError, createSession } =
    useSessionStore();

  const handleJoin = async () => {
    if (!sessionCode.trim()) return;
    await joinSession(sessionCode.trim(), deviceType);
  };

  const handleCreate = async () => {
    await createSession(deviceType);
  };

  return (
    <div className="min-h-screen bg-gray-900 text-white flex items-center justify-center">
      <div className="max-w-md w-full space-y-8 p-8">
        <div className="text-center">
          <h1 className="text-3xl font-bold mb-2">Open Karaoke Studio</h1>
          <p className="text-gray-400">Join a karaoke session</p>
        </div>

        <div className="space-y-6">
          {/* Create Session */}
          <div className="space-y-4">
            <h2 className="text-xl font-semibold">Create New Session</h2>
            <div className="space-y-2">
              <label className="block text-sm font-medium">Device Type</label>
              <select
                value={deviceType}
                onChange={(e) =>
                  setDeviceType(
                    e.target.value as "stage" | "performer" | "controller",
                  )
                }
                className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="stage">Stage (Host)</option>
                <option value="performer">Performer</option>
                <option value="controller">Controller</option>
              </select>
            </div>
            <button
              onClick={handleCreate}
              disabled={isConnecting}
              className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 px-4 py-2 rounded-md font-medium transition-colors"
            >
              {isConnecting ? "Creating..." : "Create Session"}
            </button>
          </div>

          {/* Join Session */}
          <div className="space-y-4">
            <h2 className="text-xl font-semibold">Join Existing Session</h2>
            <div className="space-y-2">
              <label className="block text-sm font-medium">Session Code</label>
              <input
                type="text"
                value={sessionCode}
                onChange={(e) => setSessionCode(e.target.value.toUpperCase())}
                placeholder="Enter 4-character code"
                maxLength={4}
                className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 uppercase"
              />
            </div>
            <div className="space-y-2">
              <label className="block text-sm font-medium">Device Type</label>
              <select
                value={deviceType}
                onChange={(e) =>
                  setDeviceType(
                    e.target.value as "stage" | "performer" | "controller",
                  )
                }
                className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="performer">Performer</option>
                <option value="controller">Controller</option>
                <option value="stage">Stage (Host)</option>
              </select>
            </div>
            <button
              onClick={handleJoin}
              disabled={isConnecting || sessionCode.length !== 4}
              className="w-full bg-green-600 hover:bg-green-700 disabled:bg-gray-600 px-4 py-2 rounded-md font-medium transition-colors"
            >
              {isConnecting ? "Joining..." : "Join Session"}
            </button>
          </div>

          {/* Error Display */}
          {connectionError && (
            <div className="p-4 bg-red-900 border border-red-700 rounded-md">
              <p className="text-red-200">{connectionError}</p>
            </div>
          )}
        </div>

        <div className="text-center text-sm text-gray-400">
          <p>
            Enter a 4-character session code to join an existing karaoke
            session,
          </p>
          <p>or create a new session to get started!</p>
        </div>
      </div>
    </div>
  );
}
