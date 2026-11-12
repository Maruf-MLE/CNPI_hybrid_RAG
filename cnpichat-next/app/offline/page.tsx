export default function OfflinePage() {
  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'linear-gradient(135deg, #0f172a 0%, #1e3a8a 100%)',
        color: 'white',
        fontFamily: 'system-ui, sans-serif',
        padding: '24px',
        textAlign: 'center',
      }}
    >
      {/* Icon */}
      <div
        style={{
          width: 80,
          height: 80,
          background: 'rgba(56, 189, 248, 0.15)',
          borderRadius: '50%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          marginBottom: 24,
          border: '2px solid rgba(56, 189, 248, 0.3)',
        }}
      >
        <svg
          width="40"
          height="40"
          viewBox="0 0 24 24"
          fill="none"
          stroke="#38bdf8"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <line x1="1" y1="1" x2="23" y2="23" />
          <path d="M16.72 11.06A10.94 10.94 0 0 1 19 12.55" />
          <path d="M5 12.55a10.94 10.94 0 0 1 5.17-2.39" />
          <path d="M10.71 5.05A16 16 0 0 1 22.56 9" />
          <path d="M1.42 9a15.91 15.91 0 0 1 4.7-2.88" />
          <path d="M8.53 16.11a6 6 0 0 1 6.95 0" />
          <line x1="12" y1="20" x2="12.01" y2="20" />
        </svg>
      </div>

      {/* Title */}
      <h1
        style={{
          fontSize: '1.75rem',
          fontWeight: 700,
          color: '#38bdf8',
          marginBottom: 12,
        }}
      >
        ইন্টারনেট সংযোগ নেই
      </h1>

      <p
        style={{
          fontSize: '1rem',
          color: '#94a3b8',
          maxWidth: 320,
          lineHeight: 1.6,
          marginBottom: 32,
        }}
      >
        CNPI Chat ব্যবহার করতে ইন্টারনেট সংযোগ প্রয়োজন। অনুগ্রহ করে আপনার নেটওয়ার্ক চেক করুন এবং আবার চেষ্টা করুন।
      </p>

      {/* Retry button */}
      <button
        onClick={() => window.location.reload()}
        style={{
          padding: '12px 28px',
          background: '#38bdf8',
          color: '#0f172a',
          border: 'none',
          borderRadius: 8,
          fontSize: '1rem',
          fontWeight: 700,
          cursor: 'pointer',
        }}
      >
        আবার চেষ্টা করুন
      </button>

      {/* Branding */}
      <p
        style={{
          marginTop: 48,
          fontSize: '0.8rem',
          color: '#475569',
        }}
      >
        CNPI Chat — Cumilla Polytechnic Institute
      </p>
    </div>
  )
}
