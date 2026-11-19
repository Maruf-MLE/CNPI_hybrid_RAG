/**
 * Simple Inline Queue Waiting Indicator
 * Shows countdown timer below user's message (minimal design)
 */

import React, { useEffect, useState } from 'react';

interface QueueMessageProps {
  queuePosition: number;
  estimatedWaitSeconds: number;
}

export default function QueueMessage({ 
  queuePosition, 
  estimatedWaitSeconds 
}: QueueMessageProps) {
  const [countdown, setCountdown] = useState(estimatedWaitSeconds);

  useEffect(() => {
    setCountdown(estimatedWaitSeconds);
  }, [estimatedWaitSeconds]);

  useEffect(() => {
    if (countdown <= 0) return;

    const timer = setInterval(() => {
      setCountdown((prev) => Math.max(0, prev - 1));
    }, 1000);

    return () => clearInterval(timer);
  }, [countdown]);

  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      gap: '8px',
      padding: '8px 12px',
      background: 'rgba(59, 130, 246, 0.1)',
      borderRadius: '8px',
      fontSize: '0.9rem',
      color: '#3b82f6',
    }}>
      {/* Loading spinner */}
      <div style={{
        width: '16px',
        height: '16px',
        border: '2px solid rgba(59, 130, 246, 0.3)',
        borderTop: '2px solid #3b82f6',
        borderRadius: '50%',
        animation: 'spin 1s linear infinite',
      }} />
      
      <span style={{ fontWeight: 500 }}>
        অপেক্ষা করুন... {formatTime(countdown)}
      </span>
      
      <span style={{
        fontSize: '0.85rem',
        color: '#64748b',
        marginLeft: 'auto',
      }}>
        সারি #{queuePosition}
      </span>

      <style jsx>{`
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}
