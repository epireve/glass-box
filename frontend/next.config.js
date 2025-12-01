/** @type {import('next').NextConfig} */
const nextConfig = {
  experimental: {
    serverActions: {
      allowedOrigins: ['localhost:3000']
    }
  },
  typescript: {
    // Ignore build errors due to React 18 types incompatibility with lucide-react
    // This is a known issue: https://github.com/lucide-icons/lucide/issues/1540
    ignoreBuildErrors: true
  }
}

module.exports = nextConfig
