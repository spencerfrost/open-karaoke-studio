import React, { useState } from "react";
import { useSessionStore } from "@/stores/sessionStore";
import { Button } from "@/components/ui/button";

interface SessionJoinFormProps {
  onSessionCodeChange?: (code: string) => void;
  onDeviceTypeChange?: (type: "performer" | "controller") => void;
}

const SessionJoinForm: React.FC<SessionJoinFormProps> = ({
  onSessionCodeChange,
  onDeviceTypeChange,
}) => {
  const [sessionCode, setSessionCode] = useState("");
  const [deviceType, setDeviceType] = useState<"performer" | "controller">(
    "performer",
  );

  const { joinSession, createSession, connectionError, isConnecting } =
    useSessionStore();

  const handleSessionCodeChange = (value: string) => {
    setSessionCode(value);
    onSessionCodeChange?.(value);
  };

  const handleDeviceTypeChange = (value: "performer" | "controller") => {
    setDeviceType(value);
    onDeviceTypeChange?.(value);
  };

  const handleJoinSession = async () => {
    if (!sessionCode.trim()) return;
    await joinSession(sessionCode.trim().toUpperCase(), deviceType);
  };

  const handleCreateSession = async () => {
    await createSession(deviceType);
  };

  return (
    <div className="flex-1 flex items-center justify-center flex-col space-y-8">
      <div className="text-center">
        <h2 className="text-3xl font-bold text-orange-peel mb-4">
          Join a Karaoke Session
        </h2>
        <p className="text-lemon-chiffon/80 mb-8">
          Enter the 4-character session code to control the karaoke performance
        </p>
      </div>

      <div className="w-full max-w-md space-y-6">
        {/* Session Code Input */}
        <div className="space-y-2">
          <label className="block text-sm font-medium text-lemon-chiffon">
            Session Code
          </label>
          <input
            type="text"
            value={sessionCode}
            onChange={(e) =>
              handleSessionCodeChange(e.target.value.toUpperCase())
            }
            placeholder="ABCD"
            maxLength={4}
            className="w-full text-center text-4xl font-bold tracking-widest bg-gray-800 border-2 border-orange-peel/50 rounded-lg px-4 py-6 focus:outline-none focus:border-orange-peel focus:ring-2 focus:ring-orange-peel/20 uppercase"
            autoFocus
          />
        </div>

        {/* Device Type Selection */}
        <div className="space-y-2">
          <label className="block text-sm font-medium text-lemon-chiffon">
            Device Type
          </label>
          <select
            value={deviceType}
            onChange={(e) =>
              handleDeviceTypeChange(
                e.target.value as "performer" | "controller",
              )
            }
            className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-md focus:outline-none focus:ring-2 focus:ring-orange-peel"
          >
            <option value="performer">Performer</option>
            <option value="controller">Controller</option>
          </select>
        </div>

        {/* Join Button */}
        <Button
          onClick={handleJoinSession}
          disabled={
            !sessionCode.trim() || sessionCode.length !== 4 || isConnecting
          }
          className="w-full bg-orange-peel hover:bg-orange-peel/80 text-black font-bold py-4 text-lg"
        >
          {isConnecting ? "Joining..." : "Join Session"}
        </Button>

        {/* Create Session Option */}
        <div className="text-center">
          <p className="text-lemon-chiffon/60 mb-2">or</p>
          <Button
            onClick={handleCreateSession}
            variant="outline"
            className="border-orange-peel/50 text-orange-peel hover:bg-orange-peel/10"
            disabled={isConnecting}
          >
            Create New Session
          </Button>
        </div>

        {/* Error Display */}
        {connectionError && (
          <div className="p-4 bg-red-900/50 border border-red-700 rounded-md">
            <p className="text-red-200 text-center">{connectionError}</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default SessionJoinForm;
