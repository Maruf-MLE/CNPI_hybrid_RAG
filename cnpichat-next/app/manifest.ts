export default function manifest() {
  return {
    name: 'CNPI RAG - AI-Powered College Information System',
    short_name: 'CNPI Chat',
    description: 'AI-powered chatbot for Cumilla Polytechnic Institute providing instant answers about classes, routines, teachers, and college information',
    start_url: '/',
    scope: '/',
    display: 'standalone',
    orientation: 'portrait',
    background_color: '#0f172a',
    theme_color: '#0f172a',
    categories: ['education', 'utilities'],
    lang: 'en',
    icons: [
      {
        src: '/favicon.ico',
        sizes: 'any',
        type: 'image/x-icon',
        purpose: 'any',
      },
      {
        src: '/CNPI_chat_remove_bg.png',
        sizes: '192x192',
        type: 'image/png',
        purpose: 'any',
      },
      {
        src: '/CNPI_chat_remove_bg.png',
        sizes: '512x512',
        type: 'image/png',
        purpose: 'any',
      },
      {
        src: '/CNPI_chat_remove_bg.png',
        sizes: '256x256',
        type: 'image/png',
        purpose: 'maskable',
      },
    ],
    screenshots: [
      {
        src: '/api/og?title=CNPI+RAG&subtitle=AI-Powered+College+Information+System',
        sizes: '1200x630',
        type: 'image/png',
        form_factor: 'wide',
        label: 'CNPI RAG Chat Interface',
      },
    ],
  }
}
