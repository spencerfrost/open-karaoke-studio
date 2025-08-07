import React, { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

interface SingerNameDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: (singerName: string) => void;
  songTitle: string;
}

export const SingerNameDialog: React.FC<SingerNameDialogProps> = ({
  isOpen,
  onClose,
  onConfirm,
  songTitle,
}) => {
  const [singerName, setSingerName] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (singerName.trim()) {
      onConfirm(singerName.trim());
      setSingerName("");
      onClose();
    }
  };

  const handleClose = () => {
    setSingerName("");
    onClose();
  };

  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Add to Karaoke Queue</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit}>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="singer-name">Singer Name</Label>
              <Input
                id="singer-name"
                type="text"
                placeholder="Enter your name"
                value={singerName}
                onChange={(e) => setSingerName(e.target.value)}
                autoFocus
              />
            </div>
            <div className="text-sm text-muted-foreground">
              Adding "{songTitle}" to the karaoke queue
            </div>
          </div>
          <DialogFooter className="mt-6">
            <Button type="button" variant="outline" onClick={handleClose}>
              Cancel
            </Button>
            <Button type="submit" disabled={!singerName.trim()}>
              Add to Queue
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
};
