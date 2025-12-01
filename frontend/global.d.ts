// Fix for React 18 types compatibility issue
// This resolves "cannot be used as a JSX component" errors

import * as React from 'react'

declare global {
  namespace JSX {
    interface Element extends React.ReactElement<any, any> {}
  }
}

export {}
