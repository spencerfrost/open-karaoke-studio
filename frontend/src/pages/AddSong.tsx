import React, { useState } from 'react';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import FileUploader from '../components/upload/FileUploader';
import YouTubeImporter from '../components/upload/YouTubeImporter';
import ProcessingQueue from '../components/upload/ProcessingQueue';
import AppLayout from '../components/layout/AppLayout';
import { uploadAndProcessAudio, processYouTubeVideo } from '../services/uploadService';
import vintageTheme from '../utils/theme';

const AddSongPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState('upload');
  const colors = vintageTheme.colors;
  
  // Handle file upload
  const handleFileUpload = async (file: File) => {
    try {
      const response = await uploadAndProcessAudio(file);
      if (response.error) {
        console.error('Error uploading file:', response.error);
        // Add proper error handling here
        return;
      }
      
      // Handle successful upload - you could update a processing queue state here
      console.log('File uploaded successfully:', response.data);
    } catch (error) {
      console.error('Upload error:', error);
    }
  };
  
  // Handle YouTube import
  const handleYouTubeImport = async (url: string, title?: string, artist?: string) => {
    try {
      const response = await processYouTubeVideo(url, { title, artist });
      if (response.error) {
        console.error('Error processing YouTube URL:', response.error);
        // Add proper error handling here
        return;
      }
      
      // Handle successful processing request
      console.log('YouTube processing initiated:', response.data);
    } catch (error) {
      console.error('YouTube processing error:', error);
    }
  };

  return (
    <AppLayout>
      <div>
        <h1 
          className="text-2xl font-semibold mb-6"
          style={{ color: colors.orangePeel }}
        >
          Add New Songs
        </h1>
        
        <Tabs 
          defaultValue="upload" 
          value={activeTab} 
          onValueChange={setActiveTab}
          className="mb-6"
        >
          <TabsList className="mb-4 p-1 rounded-lg" style={{ backgroundColor: `${colors.russet}80` }}>
            <TabsTrigger 
              value="upload" 
              className="px-4 py-2 rounded-md"
              style={activeTab === 'upload' ? {
                backgroundColor: colors.darkCyan,
                color: colors.lemonChiffon
              } : {
                backgroundColor: 'transparent',
                color: colors.lemonChiffon
              }}
            >
              Upload File
            </TabsTrigger>
            <TabsTrigger 
              value="youtube" 
              className="px-4 py-2 rounded-md"
              style={activeTab === 'youtube' ? {
                backgroundColor: colors.darkCyan,
                color: colors.lemonChiffon
              } : {
                backgroundColor: 'transparent',
                color: colors.lemonChiffon
              }}
            >
              YouTube
            </TabsTrigger>
          </TabsList>
          
          <TabsContent value="upload" className="mt-0">
            <FileUploader onFileSelect={handleFileUpload} />
          </TabsContent>
          
          <TabsContent value="youtube" className="mt-0">
            <YouTubeImporter onYouTubeImport={handleYouTubeImport} />
          </TabsContent>
        </Tabs>
        
        <div className="mt-8">
          <h2 
            className="text-xl font-semibold mb-3"
            style={{ color: colors.orangePeel }}
          >
            Processing Queue
          </h2>
          
          {/* Processing Queue component would go here */}
          {/* This would show the status of all currently processing songs */}
          {/* <ProcessingQueue /> */}
          
          {/* Placeholder for now */}
          <div 
            className="rounded-lg p-6 text-center"
            style={{ 
              backgroundColor: `${colors.lemonChiffon}10`,
              color: colors.lemonChiffon 
            }}
          >
            <p className="opacity-80">No songs currently processing</p>
          </div>
        </div>
      </div>
    </AppLayout>
  );
};

export default AddSongPage;
