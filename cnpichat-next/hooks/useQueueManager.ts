/**
 * Queue Management Hook for Chat API
 * Handles waiting queue UI and polling
 */

import { useState, useEffect, useCallback, useRef } from 'react';

interface QueueStatus {
  queued: boolean;
  queue_position?: number;
  estimated_wait_seconds?: number;
  message?: string;
  message_en?: string;
}

interface UseQueueManagerProps {
  sessionId: string;
  apiBaseUrl: string;
}

interface UseQueueManagerReturn {
  isInQueue: boolean;
  queuePosition: number | null;
  estimatedWaitSeconds: number | null;
  queueMessage: string | null;
  checkQueueStatus: () => Promise<void>;
  resetQueue: () => void;
}

export function useQueueManager({ 
  sessionId, 
  apiBaseUrl 
}: UseQueueManagerProps): UseQueueManagerReturn {
  const [isInQueue, setIsInQueue] = useState(false);
  const [queuePosition, setQueuePosition] = useState<number | null>(null);
  const [estimatedWaitSeconds, setEstimatedWaitSeconds] = useState<number | null>(null);
  const [queueMessage, setQueueMessage] = useState<string | null>(null);
  
  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null);

  const checkQueueStatus = useCallback(async () => {
    if (!sessionId) return;

    try {
      const res = await fetch(
        `${apiBaseUrl}/api/queue/status/?session_id=${sessionId}`,
        { method: 'GET' }
      );

      if (res.ok) {
        const data = await res.json();
        
        if (data.in_queue) {
          setIsInQueue(true);
          setQueuePosition(data.queue_position || null);
          setEstimatedWaitSeconds(data.estimated_wait_seconds || null);
        } else {
          // Not in queue anymore
          setIsInQueue(false);
          setQueuePosition(null);
          setEstimatedWaitSeconds(null);
          setQueueMessage(null);
        }
      }
    } catch (error) {
      console.error('Failed to check queue status:', error);
    }
  }, [sessionId, apiBaseUrl]);

  const resetQueue = useCallback(() => {
    setIsInQueue(false);
    setQueuePosition(null);
    setEstimatedWaitSeconds(null);
    setQueueMessage(null);
    
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = null;
    }
  }, []);

  // Start polling when in queue
  useEffect(() => {
    if (isInQueue && sessionId) {
      // Poll every 3 seconds
      pollIntervalRef.current = setInterval(checkQueueStatus, 3000);
      
      return () => {
        if (pollIntervalRef.current) {
          clearInterval(pollIntervalRef.current);
        }
      };
    }
  }, [isInQueue, sessionId, checkQueueStatus]);

  return {
    isInQueue,
    queuePosition,
    estimatedWaitSeconds,
    queueMessage,
    checkQueueStatus,
    resetQueue,
  };
}
