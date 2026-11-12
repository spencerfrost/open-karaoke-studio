import React from "react";
import { usePhonePresence } from "../hooks/usePhonePresence";

/**
 * Mounts usePhonePresence inside the router, for every page. Renders nothing.
 */
const PhonePresence: React.FC = () => {
  usePhonePresence();
  return null;
};

export default PhonePresence;
