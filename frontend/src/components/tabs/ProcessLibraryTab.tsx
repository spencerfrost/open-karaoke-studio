import React from "react";
import FileUpload from "@/components/FileUpload";
import ActionStatus from "@/components/ActionStatus";
import SongLibrary from "@/components/SongLibrary";

const ProcessLibraryTab: React.FC = () => {
  return (
    <div>
      <FileUpload />
      <ActionStatus />
      <SongLibrary />
    </div>
  );
};

export default ProcessLibraryTab;
