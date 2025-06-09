/**
 * React hook for real-time job updates via WebSocket
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { jobsWebSocketService } from '../services/jobsWebSocketService';
import { SongProcessingStatus, SongStatus } from '../types/Song';

interface JobData {
  id: string;
  progress?: number;
  status: string;
  error?: string;
  notes?: string;
  created_at?: string;
  started_at?: string;
  completed_at?: string;
  filename?: string;
  task_id?: string;
  artist?: string;
  title?: string;
}

/**
 * Maps backend job status to frontend SongStatus
 */
function mapBackendStatus(backendStatus: string): SongStatus {
  switch (backendStatus) {
    case "pending":
      return "queued";
    case "processing":
      return "processing";
    case "completed":
      return "processed";
    case "failed":
    case "cancelled":
      return "error";
    default:
      return "error";
  }
}

/**
 * Converts backend job data to frontend processing status
 */
function mapJobToProcessingStatus(job: JobData): SongProcessingStatus {
  return {
    id: job.id,
    progress: job.progress || 0,
    status: mapBackendStatus(job.status),
    message: job.error || job.notes || undefined,
    artist: job.artist,
    title: job.title,
  };
}

/**
 * Hook for managing real-time job updates via WebSocket
 */
export function useJobsWebSocket() {
  const [jobs, setJobs] = useState<SongProcessingStatus[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const queryClient = useQueryClient();
  const cleanupFunctionsRef = useRef<(() => void)[]>([]);

  // Update job in the list
  const updateJob = useCallback((jobData: JobData) => {
    console.log('updateJob called with:', jobData);
    const processedJob = mapJobToProcessingStatus(jobData);
    
    setJobs(prevJobs => {
      const existingIndex = prevJobs.findIndex(j => j.id === jobData.id);
      
      if (existingIndex >= 0) {
        // Update existing job
        const updatedJobs = [...prevJobs];
        updatedJobs[existingIndex] = processedJob;
        console.log('Updated existing job in list');
        
        // Remove completed/failed jobs from the processing list after a short delay
        if (processedJob.status === 'processed' || processedJob.status === 'error') {
          setTimeout(() => {
            setJobs(current => current.filter(j => j.id !== jobData.id));
          }, 3000); // Keep for 3 seconds to show completion status
        }
        
        return updatedJobs;
      } else {
        // Add new job if it's in processing state
        if (['queued', 'processing'].includes(processedJob.status)) {
          console.log('Added new job to list:', processedJob);
          return [...prevJobs, processedJob];
        }
        console.log('Job not added - status not processing/queued:', processedJob.status);
        return prevJobs;
      }
    });

    // Invalidate related React Query caches
    queryClient.invalidateQueries({ queryKey: ['processing-queue'] });
    queryClient.invalidateQueries({ queryKey: ['processing-status', jobData.id] });
  }, [queryClient]);

  // Remove job from the list
  const removeJob = useCallback((jobId: string) => {
    setJobs(prevJobs => prevJobs.filter(j => j.id !== jobId));
    queryClient.invalidateQueries({ queryKey: ['processing-queue'] });
    queryClient.invalidateQueries({ queryKey: ['processing-status', jobId] });
  }, [queryClient]);

  // Handle jobs list update (initial load)
  const handleJobsList = useCallback((data: { jobs: JobData[] }) => {
    const processingJobs = data.jobs
      .filter(job => ['pending', 'processing', 'failed'].includes(job.status))
      .map(mapJobToProcessingStatus);
    
    setJobs(processingJobs);
    setError(null);
  }, []);

  // Set up WebSocket event listeners
  useEffect(() => {
    const cleanupFunctions: (() => void)[] = [];

    try {
      // Job lifecycle events
      cleanupFunctions.push(
        jobsWebSocketService.on('job_created', updateJob),
        jobsWebSocketService.on('job_updated', updateJob),
        jobsWebSocketService.on('job_completed', updateJob),
        jobsWebSocketService.on('job_failed', updateJob),
        jobsWebSocketService.on('job_cancelled', (jobData) => {
          // For cancelled jobs, we might want to remove them immediately
          setTimeout(() => removeJob(jobData.id), 1000);
        }),
        jobsWebSocketService.on('jobs_list', handleJobsList)
      );

      // Track connection status
      const checkConnection = () => {
        setIsConnected(jobsWebSocketService.isConnectionActive());
      };

      // Check connection status periodically
      const connectionCheck = setInterval(checkConnection, 1000);
      checkConnection(); // Initial check

      cleanupFunctionsRef.current = [
        ...cleanupFunctions,
        () => clearInterval(connectionCheck)
      ];

      return () => {
        cleanupFunctionsRef.current.forEach(cleanup => cleanup());
        cleanupFunctionsRef.current = [];
      };
    } catch (err) {
      setError(err instanceof Error ? err.message : 'WebSocket connection failed');
      return () => {
        cleanupFunctionsRef.current.forEach(cleanup => cleanup());
        cleanupFunctionsRef.current = [];
      };
    }
  }, [updateJob, removeJob, handleJobsList]);

  return {
    jobs,
    isConnected,
    error,
    refetch: useCallback(() => {
      // Instead of refetching via HTTP, request a refresh via WebSocket
      if (jobsWebSocketService.isConnectionActive()) {
        // Request a fresh jobs list from the server
        jobsWebSocketService.requestJobsList();
        setError(null);
      } else {
        // Try to reconnect if not connected
        jobsWebSocketService.reconnect();
        setError('WebSocket disconnected. Attempting to reconnect...');
      }
    }, []),
  };
}

/**
 * Hook for getting a specific job's status via WebSocket
 */
export function useJobStatusWebSocket(jobId: string) {
  const [job, setJob] = useState<SongProcessingStatus | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const queryClient = useQueryClient();

  useEffect(() => {
    if (!jobId) return;

    const cleanupFunctions: (() => void)[] = [];

    // Update this specific job
    const updateThisJob = (jobData: JobData) => {
      if (jobData.id === jobId) {
        setJob(mapJobToProcessingStatus(jobData));
        queryClient.invalidateQueries({ queryKey: ['processing-status', jobId] });
      }
    };

    try {
      cleanupFunctions.push(
        jobsWebSocketService.on('job_created', updateThisJob),
        jobsWebSocketService.on('job_updated', updateThisJob),
        jobsWebSocketService.on('job_completed', updateThisJob),
        jobsWebSocketService.on('job_failed', updateThisJob),
        jobsWebSocketService.on('job_cancelled', updateThisJob)
      );

      // Track connection status
      const checkConnection = () => {
        setIsConnected(jobsWebSocketService.isConnectionActive());
      };

      const connectionCheck = setInterval(checkConnection, 1000);
      checkConnection();

      cleanupFunctions.push(() => clearInterval(connectionCheck));

      return () => {
        cleanupFunctions.forEach(cleanup => cleanup());
      };
    } catch (err) {
      setError(err instanceof Error ? err.message : 'WebSocket connection failed');
      return () => {
        cleanupFunctions.forEach(cleanup => cleanup());
      };
    }
  }, [jobId, queryClient]);

  // Fetch initial job status
  useEffect(() => {
    const fetchInitialJob = async () => {
      if (!jobId) return;
      
      try {
        const response = await fetch(`/api/jobs/${jobId}`);
        if (!response.ok) {
          throw new Error(`HTTP error! Status: ${response.status}`);
        }
        const data: JobData = await response.json();
        setJob(mapJobToProcessingStatus(data));
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch job status');
      }
    };

    fetchInitialJob();
  }, [jobId]);

  return {
    job,
    isConnected,
    error,
  };
}
