import { useRegisterSW } from "virtual:pwa-register/react";
import { createLogger } from "@/lib/logger";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";

const logger = createLogger("component:PWAUpdatePrompt");

export function PWAUpdatePrompt() {
  const {
    needRefresh: [needRefresh],
    updateServiceWorker,
  } = useRegisterSW({
    onRegistered(r) {
      logger.info("Service worker registered", { registration: r });
    },
    onRegisterError(error) {
      logger.error("Service worker registration failed", { error });
    },
  });

  return (
    <AlertDialog open={needRefresh}>
      <AlertDialogContent
        // Prevent closing via Escape or overlay click
        onEscapeKeyDown={(e) => e.preventDefault()}
        onPointerDownOutside={(e) => e.preventDefault()}
      >
        <AlertDialogHeader>
          <AlertDialogTitle>Update available</AlertDialogTitle>
          <AlertDialogDescription>
            A new version of Open Karaoke Studio has been deployed. Update now
            to continue using the app.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogAction onClick={() => updateServiceWorker(true)}>
            Update now
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
