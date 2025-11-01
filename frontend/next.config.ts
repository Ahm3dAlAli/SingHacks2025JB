import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Enable standalone output for Docker deployment
  output: 'standalone',

  // Configure API rewrites to backend services
  async rewrites() {
    return [
      {
        source: '/api/tae/:path*',
        destination: `${process.env.NEXT_PUBLIC_TAE_API_URL || 'http://tae-service:8002'}/:path*`,
      },
      {
        source: '/api/regulatory/:path*',
        destination: `${process.env.NEXT_PUBLIC_REGULATORY_API_URL || 'http://regulatory-service:8003'}/:path*`,
      },
      {
        source: '/api/remediation/:path*',
        destination: `${process.env.NEXT_PUBLIC_REMEDIATION_API_URL || 'http://remediation-service:8004'}/:path*`,
      },
    ];
  },
};

export default nextConfig;
