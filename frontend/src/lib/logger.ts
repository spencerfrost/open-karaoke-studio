import log from "loglevel";

// Set log level based on environment
const logLevel =
  import.meta.env.VITE_LOG_LEVEL || (import.meta.env.PROD ? "warn" : "debug");

log.setLevel(logLevel as log.LogLevelDesc);

// Create namespace-based loggers for better organization
export function createLogger(namespace: string) {
  const logger = log.getLogger(namespace);
  return logger;
}

// Export default logger
export const logger = log;
