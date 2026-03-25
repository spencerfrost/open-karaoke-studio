import React from "react";
import { Navigate } from "react-router-dom";
import { useAuthStore } from "@/stores/authStore";

interface HostGuardProps {
  children: React.ReactNode;
}

const HostGuard: React.FC<HostGuardProps> = ({ children }) => {
  const { user, isAuthenticated } = useAuthStore();

  if (!isAuthenticated || !(user?.isHost || user?.isAdmin)) {
    return <Navigate to="/join" replace />;
  }

  return <>{children}</>;
};

export default HostGuard;
