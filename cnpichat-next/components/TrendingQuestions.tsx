'use client';

import React, { useEffect, useState } from 'react';

interface TrendingQuestion {
  id: number;
  question: string;
  category: string;
  click_count: number;
}

interface TrendingQuestionsProps {
  apiBaseUrl: string;
  onQuestionClick: (question: string, questionId: number) => void;
  dismissed: boolean;
  onDismiss: () => void;
}

export default function TrendingQuestions({ 
  apiBaseUrl,
  onQuestionClick,
  dismissed,
  onDismiss,
}: TrendingQuestionsProps) {
  const [questions, setQuestions] = useState<TrendingQuestion[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    const doFetch = async () => {
      try {
        const res = await fetch(`${apiBaseUrl}/api/trending-questions/`);
        if (!cancelled && res.ok) {
          const data = await res.json();
          if (!cancelled && Array.isArray(data.questions) && data.questions.length > 0) {
            setQuestions(data.questions);
          }
        }
      } catch {
        // silently ignore
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    doFetch();
    return () => { cancelled = true; };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const handleQuestionClick = (question: TrendingQuestion) => {
    fetch(`${apiBaseUrl}/api/trending-questions/${question.id}/click/`, {
      method: 'POST',
    }).catch(() => {});

    onQuestionClick(question.question, question.id);
  };

  if (loading || questions.length === 0 || dismissed) {
    return null;
  }

  return (
    <div style={{
      padding: '10px 14px 8px',
      background: '#f8fafc',
      borderBottom: '1px solid #e2e8f0',
    }}>
      {/* Header */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        marginBottom: '8px',
      }}>
        <span style={{
          fontSize: '0.72rem',
          fontWeight: 700,
          color: '#64748b',
          letterSpacing: '0.03em',
        }}>
          🔥 ট্রেন্ডিং প্রশ্ন
        </span>

        <button
          onClick={onDismiss}
          title="বন্ধ করুন"
          style={{
            background: 'none',
            border: 'none',
            cursor: 'pointer',
            padding: '2px 6px',
            borderRadius: '4px',
            color: '#94a3b8',
            fontSize: '0.85rem',
            lineHeight: 1,
            transition: 'all 0.15s',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.color = '#ef4444';
            e.currentTarget.style.background = '#fee2e2';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.color = '#94a3b8';
            e.currentTarget.style.background = 'none';
          }}
        >
          ✕
        </button>
      </div>

      {/* Vertical list */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
        {questions.map((q) => (
          <button
            key={q.id}
            onClick={() => handleQuestionClick(q)}
            style={{
              width: '100%',
              padding: '8px 12px',
              background: 'white',
              border: '1px solid #e2e8f0',
              borderRadius: '8px',
              fontSize: '0.85rem',
              color: '#1e293b',
              cursor: 'pointer',
              textAlign: 'left',
              transition: 'all 0.15s',
              boxShadow: '0 1px 2px rgba(0,0,0,0.05)',
              lineHeight: 1.4,
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = '#eff6ff';
              e.currentTarget.style.borderColor = '#3b82f6';
              e.currentTarget.style.color = '#1d4ed8';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'white';
              e.currentTarget.style.borderColor = '#e2e8f0';
              e.currentTarget.style.color = '#1e293b';
            }}
          >
            {q.question}
          </button>
        ))}
      </div>
    </div>
  );
}
