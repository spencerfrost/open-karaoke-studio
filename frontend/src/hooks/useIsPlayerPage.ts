import { useLocation } from "react-router-dom";

/**
 * Hook to detect if the current route is a player-related page.
 * When on these pages, the mini-player should NOT be shown
 * (since the main player is already visible).
 */
export function useIsPlayerPage(): boolean {
  const location = useLocation();

  // Player-related routes where mini-player should NOT show
  const playerRoutes = [
    "/stage", // Stage view (full player experience)
    "/controls", // Performance controls (player is visible on stage device)
  ];

  return playerRoutes.some((route) => location.pathname.startsWith(route));
}

export default useIsPlayerPage;
