import React from "react";
import { BrowserRouter as Router } from "react-router-dom";
import ProcessLibraryTab from "@/components/tabs/ProcessLibraryTab";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

const App: React.FC = () => {
  return (
    <Router>
      <div className="container mx-auto p-4">
        <h1 className="text-2xl font-bold mb-4">Open Karaoke Studio</h1>
        <Tabs default-value="process">
          <TabsList className="mb-4">
            <TabsTrigger value="process" >Process & Library</TabsTrigger>
            <TabsTrigger value="settings">Settings</TabsTrigger>
            <TabsTrigger value="player">Player</TabsTrigger>
          </TabsList>
          {/* default to Process & Library tab */}
          <TabsContent value="process">
            <ProcessLibraryTab /> {/* Use the new tab component */}
          </TabsContent>
          <TabsContent value="settings">Settings content</TabsContent>
          <TabsContent value="player">Player content</TabsContent>
        </Tabs>
      </div>
    </Router>
  );
};

export default App;
