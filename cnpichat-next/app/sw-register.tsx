'use client'

import { useEffect } from 'react'

export default function ServiceWorkerRegistrar() {
  useEffect(() => {
    if ('serviceWorker' in navigator) {
      window.addEventListener('load', () => {
        navigator.serviceWorker
          .register('/sw.js', { scope: '/' })
          .then((registration) => {
            console.log('[SW] Registered:', registration.scope)
          })
          .catch((error) => {
            console.warn('[SW] Registration failed:', error)
          })
      })
    }
  }, [])

  return null
}
