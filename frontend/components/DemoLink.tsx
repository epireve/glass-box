'use client'

import Link from 'next/link'
import { useSearchParams } from 'next/navigation'
import { ComponentProps, Suspense } from 'react'

type DemoLinkProps = ComponentProps<typeof Link>

// Inner component that uses useSearchParams
function DemoLinkInner({ href, ...props }: DemoLinkProps) {
  const searchParams = useSearchParams()
  const isDemoMode = searchParams.get('mode') === 'demo'

  // Preserve ?mode=demo if currently in demo mode
  const finalHref = isDemoMode && typeof href === 'string' && !href.includes('?')
    ? `${href}?mode=demo`
    : href

  return <Link href={finalHref} {...props} />
}

// Wrapper with Suspense boundary - fallback renders a normal Link during SSR
export function DemoLink({ href, ...props }: DemoLinkProps) {
  return (
    <Suspense fallback={<Link href={href} {...props} />}>
      <DemoLinkInner href={href} {...props} />
    </Suspense>
  )
}
