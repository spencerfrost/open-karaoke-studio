import React, { useState, useRef, DragEvent, ChangeEvent } from 'react';
import { Upload, X } from 'lucide-react';
import { isAudioFile } from '../../utils/validators';
import vintageTheme from '../../utils/theme';

interface FileUploaderProps {
  onFileSelect: (file: File) => void;
  accept?: string;
  maxSize?: number; // In bytes
}

const FileUploader: React.FC<FileUploaderProps> = ({
  onFileSelect,
  accept = 'audio/*',
  maxSize = 100 * 1024 * 1024, // 100MB default
}) => {
  const [dragActive, setDragActive] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const colors = vintageTheme.colors;

  // Handle drag events
  const handleDrag = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  // Handle drop event
  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFile(e.dataTransfer.files[0]);
    }
  };

  // Handle file input change
  const handleChange = (e: ChangeEvent<HTMLInputElement>) => {
    e.preventDefault();
    
    if (e.target.files && e.target.files[0]) {
      handleFile(e.target.files[0]);
    }
  };

  // Handle file selection
  const handleFile = (file: File) => {
    // Validate file
    if (!isAudioFile(file)) {
      setError('Please select an audio file.');
      return;
    }
    
    if (file.size > maxSize) {
      setError(`File size exceeds the maximum limit of ${maxSize / (1024 * 1024)}MB.`);
      return;
    }
    
    setError(null);
    setSelectedFile(file);
    onFileSelect(file);
  };

  // Trigger file input click
  const onButtonClick = () => {
    inputRef.current?.click();
  };

  // Clear selected file
  const clearSelectedFile = () => {
    setSelectedFile(null);
    if (inputRef.current) {
      inputRef.current.value = '';
    }
  };

  // Card styles
  const cardStyle = {
    backgroundColor: colors.lemonChiffon,
    color: colors.russet,
    borderColor: dragActive ? colors.darkCyan : colors.orangePeel,
    boxShadow: dragActive 
      ? `0 0 0 2px ${colors.darkCyan}, 0 4px 6px rgba(0, 0, 0, 0.1)` 
      : `0 4px 6px rgba(0, 0, 0, 0.1), inset 0 0 0 1px ${colors.orangePeel}`,
  };

  // Button style
  const buttonStyle = {
    backgroundColor: colors.darkCyan,
    color: colors.lemonChiffon,
    border: `1px solid ${colors.lemonChiffon}`,
  };

  return (
    <div className="w-full">
      {/* File input element (hidden) */}
      <input
        ref={inputRef}
        type="file"
        className="hidden"
        accept={accept}
        onChange={handleChange}
      />
      
      {/* Drag and drop area */}
      <div
        className={`rounded-lg p-5 border-2 border-dashed flex flex-col items-center justify-center transition-all ${
          dragActive ? 'border-solid' : ''
        }`}
        style={cardStyle}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
      >
        {selectedFile ? (
          // Display selected file
          <div className="w-full">
            <div className="flex items-center justify-between mb-2">
              <h3 className="font-medium">Selected File</h3>
              <button 
                onClick={clearSelectedFile}
                className="text-sm p-1 rounded-full hover:bg-gray-200 transition-colors"
                aria-label="Clear selected file"
              >
                <X size={16} style={{ color: colors.rust }} />
              </button>
            </div>
            <div 
              className="bg-white bg-opacity-50 p-3 rounded border"
              style={{ borderColor: colors.orangePeel }}
            >
              <p className="font-medium truncate">{selectedFile.name}</p>
              <p className="text-sm opacity-75">
                {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB
              </p>
            </div>
          </div>
        ) : (
          // Upload prompt
          <>
            <Upload size={48} style={{ color: colors.darkCyan }} className="mb-3" />
            <p className="text-center mb-1">Drag and drop your audio files here</p>
            <p className="text-sm opacity-75 text-center mb-3">or</p>
            <button 
              className="px-4 py-2 rounded transition-colors hover:opacity-90"
              style={buttonStyle}
              onClick={onButtonClick}
            >
              Browse Files
            </button>
          </>
        )}
      </div>
      
      {/* Error message */}
      {error && (
        <div 
          className="mt-2 p-2 rounded text-sm"
          style={{ backgroundColor: `${colors.rust}20`, color: colors.rust }}
        >
          {error}
        </div>
      )}
    </div>
  );
};

export default FileUploader;
