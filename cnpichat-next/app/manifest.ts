export default function manifest() {
  return {
    name: 'CNPI RAG - AI-Powered College Information System',
    short_name: 'CNPI RAG',
    description: 'AI-powered chatbot for Cumilla Polytechnic Institute providing instant answers about classes, routines, teachers, and college information',
    start_url: '/',
    display: 'standalone',
    background_color: '#0f172a',
    theme_color: '#0f172a',
    icons: [
      {
        src: '/favicon.ico',
        sizes: 'any',
        type: 'image/x-icon',
      },
      {
        src: '/icon-192.png',
        sizes: '192x192',
        type: 'image/png',
      },
      {
        src: '/icon-512.png',
        sizes: '512x512',
        type: 'image/png',
      },
    ],
  }
}
