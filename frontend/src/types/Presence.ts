/**
 * Whether a singer's phone is open, as the session socket reports it.
 *
 * Keyed by roster seat, never by device: device ids are the session credential,
 * so the server never broadcasts them. Only seats with a phone linked appear -
 * a walk-up the host typed in has no phone to open.
 */
export interface PerformerPresence {
  performerId: number;
  /** At least one of the phone's pages has a live socket. */
  connected: boolean;
  /** At least one of them is on screen, not backgrounded or locked. */
  visible: boolean;
  /** One of them is on screen and showing the performance controls. */
  onControls: boolean;
}
