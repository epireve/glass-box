'use client'

import { useState, useEffect } from 'react'

// Check if running on localhost (unless ?mode=demo is set)
const checkIsLocalhost = () => {
  if (typeof window === 'undefined') return true

  // Check for ?mode=demo query param to force demo mode
  const urlParams = new URLSearchParams(window.location.search)
  if (urlParams.get('mode') === 'demo') {
    return false // Force demo mode
  }

  const hostname = window.location.hostname
  return hostname === 'localhost' || hostname === '127.0.0.1' || hostname.startsWith('192.168.')
}

// Get link href with demo mode preserved
export const getDemoAwareHref = (path: string): string => {
  if (typeof window === 'undefined') return path

  const urlParams = new URLSearchParams(window.location.search)
  if (urlParams.get('mode') === 'demo') {
    return `${path}?mode=demo`
  }
  return path
}

export function useDemoMode() {
  const [isLocal, setIsLocal] = useState(true)

  useEffect(() => {
    setIsLocal(checkIsLocalhost())
  }, [])

  return { isLocal, getDemoAwareHref }
}
