/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: 'export',
  distDir: 'dist',
  trailingSlash: true,
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'https://travel-ai-backend-vwwk.onrender.com/api/v1',
  },
  images: {
    unoptimized: true,
    domains: ['localhost', 'maps.googleapis.com'],
  },
};

module.exports = nextConfig;
