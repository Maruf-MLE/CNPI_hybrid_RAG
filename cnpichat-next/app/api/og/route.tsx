import { ImageResponse } from 'next/og'
import { NextRequest } from 'next/server'

export const runtime = 'edge'

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url)
  const title = searchParams.get('title') || 'CNPI RAG'
  const subtitle = searchParams.get('subtitle') || 'AI-Powered College Information System'

  return new ImageResponse(
    (
      <div
        style={{
          width: 1200,
          height: 630,
          background: 'linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #0f172a 100%)',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          fontFamily: 'system-ui, sans-serif',
          position: 'relative',
          overflow: 'hidden',
        }}
      >
        {/* Background grid pattern */}
        <div
          style={{
            position: 'absolute',
            inset: 0,
            backgroundImage:
              'radial-gradient(circle at 25px 25px, #334155 1px, transparent 0)',
            backgroundSize: '50px 50px',
            opacity: 0.3,
          }}
        />

        {/* Glow effect */}
        <div
          style={{
            position: 'absolute',
            width: 600,
            height: 600,
            borderRadius: '50%',
            background: 'radial-gradient(circle, rgba(56,189,248,0.15) 0%, transparent 70%)',
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
          }}
        />

        {/* Badge */}
        <div
          style={{
            background: 'rgba(56,189,248,0.1)',
            border: '1px solid rgba(56,189,248,0.3)',
            borderRadius: 100,
            padding: '8px 24px',
            marginBottom: 32,
            display: 'flex',
            alignItems: 'center',
            gap: 8,
          }}
        >
          <div style={{ fontSize: 14, color: '#38bdf8', fontWeight: 600, letterSpacing: 2 }}>
            🤖 AI POWERED
          </div>
        </div>

        {/* Logo + Title */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 24, marginBottom: 24 }}>
          <div
            style={{
              width: 80,
              height: 80,
              background: 'linear-gradient(135deg, #1e3a8a, #38bdf8)',
              borderRadius: 20,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: 40,
              fontWeight: 900,
              color: 'white',
              boxShadow: '0 0 40px rgba(56,189,248,0.4)',
            }}
          >
            C
          </div>
          <div style={{ fontSize: 60, fontWeight: 800, color: '#f1f5f9', letterSpacing: -2 }}>
            {title}
          </div>
        </div>

        {/* Subtitle */}
        <div
          style={{
            fontSize: 26,
            color: '#94a3b8',
            textAlign: 'center',
            maxWidth: 800,
            lineHeight: 1.4,
            marginBottom: 48,
          }}
        >
          {subtitle}
        </div>

        {/* Feature chips */}
        <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', justifyContent: 'center' }}>
          {['RAG Technology', 'Bengali Support', 'Class Routines', 'Teacher Info', 'Lab Details'].map(
            (feature) => (
              <div
                key={feature}
                style={{
                  background: 'rgba(30,41,59,0.8)',
                  border: '1px solid #334155',
                  borderRadius: 100,
                  padding: '8px 20px',
                  fontSize: 16,
                  color: '#cbd5e1',
                }}
              >
                {feature}
              </div>
            )
          )}
        </div>

        {/* URL at bottom */}
        <div
          style={{
            position: 'absolute',
            bottom: 32,
            display: 'flex',
            alignItems: 'center',
            gap: 8,
          }}
        >
          <div style={{ width: 8, height: 8, borderRadius: '50%', background: '#22c55e' }} />
          <div style={{ fontSize: 18, color: '#64748b' }}>cnpichat.netlify.app</div>
        </div>
      </div>
    ),
    { width: 1200, height: 630 }
  )
}
