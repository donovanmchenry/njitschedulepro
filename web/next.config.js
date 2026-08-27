/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  reactStrictMode: true,
  swcMinify: true,
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
