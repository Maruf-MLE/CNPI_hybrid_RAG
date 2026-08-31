import { ImageResponse } from 'next/og'

export const size = { width: 180, height: 180 }
export const contentType = 'image/png'

export default function AppleTouchIcon() {
  return new ImageResponse(
    (
      <div
        style={{
          width: 180,
          height: 180,
          background: 'linear-gradient(135deg, #0f172a 0%, #1e3a8a 100%)',
          borderRadius: 40,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          fontFamily: 'system-ui, sans-serif',
          gap: 4,
        }}
      >
        <div style={{ fontSize: 64, color: '#38bdf8', fontWeight: 700 }}>C</div>
        <div style={{ fontSize: 18, color: '#94a3b8', fontWeight: 600, letterSpacing: 2 }}>CNPI</div>
      </div>
    ),
    { ...size }
  )
}
