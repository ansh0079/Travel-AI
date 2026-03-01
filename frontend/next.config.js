/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: 'standandalone',
  distDir: '.next',
  trailingSlash: false,
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'https://travel-ai-backend-vwwk.onrender.com/api/v1',
  },
  images: {
    unoptimized: false,
    domains: ['localhost', 'maps.googleapis.com', 'images.unsplash.com'],
  },
};

module.exports = nextConfig;
