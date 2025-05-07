interface WebSocketStatusProps {
  connected: boolean;
  className?: string;
}

const WebSocketStatus = ({ connected, className }: WebSocketStatusProps) => {
  return (
    <div
      className={`flex items-center gap-2 bg-russet/70 rounded py-2 px-3 ${className}`}
    >
      {connected ? (
        <div className="flex items-center gap-2">
          <span className="h-2 w-2 rounded-full bg-dark-cyan animate-pulse"></span>
          <span className="text-sm text-dark-cyan">Live</span>
        </div>
      ) : (
        <div className="flex items-center gap-2">
          <span className="h-2 w-2 rounded-full bg-rust animate-pulse"></span>
          <span className="text-sm text-rust">Connecting...</span>
        </div>
      )}
    </div>
  );
};

export default WebSocketStatus;
