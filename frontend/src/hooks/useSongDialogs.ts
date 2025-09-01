import { useState } from "react";

export type DialogType = "details" | "singer" | "delete" | null;

export const useSongDialogs = () => {
  const [activeDialog, setActiveDialog] = useState<DialogType>(null);

  const openDialog = (dialog: DialogType) => setActiveDialog(dialog);
  const closeDialog = () => setActiveDialog(null);

  const isDialogOpen = (dialog: DialogType) => activeDialog === dialog;

  return {
    activeDialog,
    openDialog,
    closeDialog,
    isDialogOpen,
  };
};