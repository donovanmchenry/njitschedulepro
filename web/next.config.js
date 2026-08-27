const path = require('path');

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  outputFileTracingRoot: path.join(__dirname, '..'),
  allowedDevOrigins: ['127.0.0.1', 'localhost'],
  reactStrictMode: true,
  async headers() {
    return [
      {
        source: '/catalog/:path*',
        headers: [
          {
            key: 'Cache-Control',
            value: 'public, max-age=300, s-maxage=300, stale-while-revalidate=86400',
          },
        ],
      },
    ];
  },
  async rewrites() {
    if (!process.env.NEXT_PUBLIC_API_BASE_URL) {
      return [
        {
          source: '/api/:path*',
          destination: `${process.env.API_PROXY_TARGET || 'http://localhost:8000'}/:path*`,
        },
      ];
    }
    return [];
  },
};

module.exports = nextConfig;
