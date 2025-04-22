import React, { useEffect, useState } from 'react';
import { Music, X } from 'lucide-react';
import { SongProcessingStatus } from '../../types/Song';
import { getProcessingQueue, cancelProcessing } from '../../services/uploadService';
import vintageTheme from '../../utils/theme';

interface ProcessingQueueProps {
  className?: string;
  refreshInterval?: number; // in milliseconds
}

const ProcessingQueue: React.FC<ProcessingQueueProps> = ({
  className = '',
  refreshInterval = 5000, // Default to 5 seconds
}) => {
  const [processingItems, setProcessingItems] = useState<SongProcessingStatus[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const colors = vintageTheme.colors;

  // Fetch processing queue on component mount and at regular intervals
  useEffect(() => {
    const fetchQueue = async () => {
      try {
        setIsLoading(true);
        const response = await getProcessingQueue();
        setIsLoading(false);
        
        if (response.error) {
          setError(response.error);
          return;
        }
        
        if (response.data) {
          setProcessingItems(response.data);
        }
      } catch (err) {
        setIsLoading(false);
        setError('Failed to load processing queue');
        console.error('Error fetching processing queue:', err);
      }
    };
    
    // Initial fetch
    fetchQueue();
    
    // Set up periodic refresh
    const intervalId = setInterval(fetchQueue, refreshInterval);
    
    // Clean up on unmount
    return () => {
      clearInterval(intervalId);
    };
  }, [refreshInterval]);

  // Handle canceling a processing task
  const handleCancel = async (taskId: string) => {
    try {
      const response = await cancelProcessing(taskId);
      
      if (response.error) {
        setError(response.error);
        return;
      }
      
      if (response.data && response.data.success) {
        // Remove from local state
        setProcessingItems(items => items.filter(item => item.id !== taskId));
      }
    } catch (err) {
      setError('Failed to cancel processing');
      console.error('Error canceling processing:', err);
    }
  };

  // Card style
  const cardStyle = {
    backgroundColor: colors.lemonChiffon,
    color: colors.russet,
    overflow: 'hidden',
  };

  // If no items and not loading, show empty message
  if (!isLoading && processingItems.length === 0) {
    return (
      <div 
        className={`rounded-lg p-6 text-center ${className}`}
        style={{ 
          backgroundColor: `${colors.lemonChiffon}10`,
          color: colors.lemonChiffon 
        }}
      >
        <p className="opacity-80">No songs currently processing</p>
      </div>
    );
  }

  return (
    <div className={className}>
      {/* Error message */}
      {error && (
        <div 
          className="mb-3 p-3 rounded text-sm"
          style={{ backgroundColor: `${colors.rust}20`, color: colors.rust }}
        >
          {error}
        </div>
      )}
      
      {/* Loading state */}
      {isLoading && processingItems.length === 0 && (
        <div 
          className="rounded-lg p-4 text-center"
          style={{ 
            backgroundColor: `${colors.lemonChiffon}10`,
            color: colors.lemonChiffon 
          }}
        >
          Loading processing queue...
        </div>
      )}
      
      {/* Processing items list */}
      <div 
        className="rounded-lg"
        style={{
          ...cardStyle,
          display: processingItems.length ? 'block' : 'none'
        }}
      >
        {processingItems.map((item) => (
          <div 
            key={item.id} 
            className="p-3 flex items-center border-b"
            style={{ borderColor: `${colors.orangePeel}30` }}
          >
            <div 
              className="h-10 w-10 rounded-md flex items-center justify-center mr-3"
              style={{ backgroundColor: `${colors.orangePeel}20` }}
            >
              <Music size={20} style={{ color: colors.darkCyan }} />
            </div>
            <div className="flex-1">
              <h4 className="font-medium truncate">
                {item.id}
                {item.message && ` - ${item.message}`}
              </h4>
              <div className="flex items-center">
                <div 
                  className="h-1 rounded-full flex-1 mr-2"
                  style={{ backgroundColor: `${colors.russet}30` }}
                >
                  <div 
                    className="h-1 rounded-full"
                    style={{ 
                      backgroundColor: item.status === 'error' ? colors.rust : colors.orangePeel,
                      width: `${item.progress}%`
                    }}
                  ></div>
                </div>
                <span className="text-xs opacity-75">{item.progress}%</span>
              </div>
              {item.status === 'error' && (
                <p className="text-xs mt-1" style={{ color: colors.rust }}>
                  Processing error
                </p>
              )}
            </div>
            <button
              className="text-sm p-2 rounded-full hover:bg-gray-200 transition-colors"
              onClick={() => handleCancel(item.id)}
              aria-label="Cancel processing"
              style={{ color: colors.rust }}
            >
              <X size={16} />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
};

export default ProcessingQueue;
