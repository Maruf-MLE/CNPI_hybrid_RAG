/**
 * Queue Waiting UI Component
 * Shows user their position in queue with countdown timer
 */

import React, { useEffect, useState } from 'react';

interface QueueWaitingProps {
  queuePosition: number;
  estimatedWaitSeconds: number;
  onCancel?: () => void;
}

export default function QueueWaiting({ 
  queuePosition, 
  estimatedWaitSeconds,
  onCancel 
}: QueueWaitingProps) {
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
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      background: 'rgba(15, 23, 42, 0.95)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 9999,
      padding: '24px',
    }}>
      <div style={{
        background: 'linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%)',
        borderRadius: '16px',
        padding: '32px',
        maxWidth: '400px',
        width: '100%',
        textAlign: 'center',
        boxShadow: '0 20px 60px rgba(0, 0, 0, 0.4)',
        border: '1px solid rgba(59, 130, 246, 0.3)',
      }}>
        {/* Queue Icon */}
        <div style={{
          width: '80px',
          height: '80px',
          background: 'rgba(255, 255, 255, 0.1)',
          borderRadius: '50%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          margin: '0 auto 24px',
          border: '3px solid rgba(255, 255, 255, 0.2)',
        }}>
          <svg
            width="40"
            height="40"
            viewBox="0 0 24 24"
            fill="none"
            stroke="white"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <circle cx="12" cy="12" r="10" />
            <polyline points="12 6 12 12 16 14" />
          </svg>
        </div>

        {/* Title */}
        <h2 style={{
          fontSize: '1.5rem',
          fontWeight: 700,
          color: 'white',
          marginBottom: '12px',
        }}>
          অনুগ্রহ করে অপেক্ষা করুন
        </h2>

        <p style={{
          fontSize: '0.9rem',
          color: 'rgba(255, 255, 255, 0.7)',
          marginBottom: '24px',
        }}>
          অনেক ব্যবহারকারী একসাথে চ্যাট করছেন
        </p>

        {/* Queue Position */}
        <div style={{
          background: 'rgba(255, 255, 255, 0.1)',
          borderRadius: '12px',
          padding: '16px',
          marginBottom: '16px',
        }}>
          <div style={{
            fontSize: '0.85rem',
            color: 'rgba(255, 255, 255, 0.6)',
            marginBottom: '8px',
          }}>
            সারিতে আপনার অবস্থান
          </div>
          <div style={{
            fontSize: '2.5rem',
            fontWeight: 700,
            color: 'white',
          }}>
            #{queuePosition}
          </div>
        </div>

        {/* Countdown Timer */}
        <div style={{
          background: 'rgba(255, 255, 255, 0.1)',
          borderRadius: '12px',
          padding: '16px',
          marginBottom: '24px',
        }}>
          <div style={{
            fontSize: '0.85rem',
            color: 'rgba(255, 255, 255, 0.6)',
            marginBottom: '8px',
          }}>
            আনুমানিক সময়
          </div>
          <div style={{
            fontSize: '2rem',
            fontWeight: 700,
            color: '#60a5fa',
            fontFamily: 'monospace',
          }}>
            {formatTime(countdown)}
          </div>
        </div>

        {/* Loading Animation */}
        <div style={{
          display: 'flex',
          justifyContent: 'center',
          gap: '8px',
          marginBottom: '24px',
        }}>
          {[0, 1, 2].map((i) => (
            <div
              key={i}
              style={{
                width: '8px',
                height: '8px',
                borderRadius: '50%',
                background: 'white',
                animation: `pulse 1.5s ease-in-out ${i * 0.2}s infinite`,
              }}
            />
          ))}
        </div>

        {/* Info Text */}
        <p style={{
          fontSize: '0.85rem',
          color: 'rgba(255, 255, 255, 0.5)',
          marginBottom: '16px',
          lineHeight: 1.6,
        }}>
          একবারে সর্বোচ্চ ৩ জন ব্যবহারকারী চ্যাট করতে পারেন। শীঘ্রই আপনার পালা আসবে।
        </p>

        {/* Cancel Button */}
        {onCancel && (
          <button
            onClick={onCancel}
            style={{
              padding: '10px 24px',
              background: 'rgba(239, 68, 68, 0.2)',
              color: 'white',
              border: '1px solid rgba(239, 68, 68, 0.4)',
              borderRadius: '8px',
              fontSize: '0.9rem',
              fontWeight: 600,
              cursor: 'pointer',
              transition: 'all 0.2s',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = 'rgba(239, 68, 68, 0.3)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'rgba(239, 68, 68, 0.2)';
            }}
          >
            বাতিল করুন
          </button>
        )}
      </div>

      <style jsx>{`
        @keyframes pulse {
          0%, 100% {
            opacity: 0.3;
            transform: scale(1);
          }
          50% {
            opacity: 1;
            transform: scale(1.2);
          }
        }
      `}</style>
    </div>
  );
}
