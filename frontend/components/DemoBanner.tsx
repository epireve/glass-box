'use client'

import { useState } from 'react'
import { Info, X } from 'lucide-react'

interface DemoBannerProps {
  isLocal: boolean
}

export function DemoBanner({ isLocal }: DemoBannerProps) {
  const [showBanner, setShowBanner] = useState(true)

  if (isLocal || !showBanner) return null

  return (
    <div className="bg-gradient-to-r from-amber-500/10 via-orange-500/10 to-amber-500/10 border-b border-amber-500/20">
      <div className="px-6 py-2.5 flex items-center gap-3">
        <Info className="h-4 w-4 text-amber-500 flex-shrink-0" />
        <p className="text-sm text-amber-600 dark:text-amber-400 flex-1">
          <strong>Demo Mode</strong> — Viewing pre-recorded results. Run locally with backend for live detection.
        </p>
        <button
          onClick={() => setShowBanner(false)}
          className="p-1 hover:bg-amber-500/20 rounded-md transition-colors flex-shrink-0"
          aria-label="Dismiss banner"
        >
          <X className="h-4 w-4 text-amber-500" />
        </button>
      </div>
    </div>
  )
}
