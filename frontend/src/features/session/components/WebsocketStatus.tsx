interface WebSocketStatusProps {
  connected: boolean;
  className?: string;
}

const WebSocketStatus = ({ connected, className }: WebSocketStatusProps) => {
  return (
    <div
      className={`flex items-center gap-2 bg-surface/70 rounded py-2 px-3 ${className}`}
    >
      {connected ? (
        <div className="flex items-center gap-2">
          <span className="h-2 w-2 rounded-full bg-accent animate-pulse"></span>
          <span className="text-sm text-accent">Live</span>
        </div>
      ) : (
        <div className="flex items-center gap-2">
          <span className="h-2 w-2 rounded-full bg-secondary animate-pulse"></span>
          <span className="text-sm text-secondary">Connecting...</span>
        </div>
      )}
    </div>
  );
};

export default WebSocketStatus;
