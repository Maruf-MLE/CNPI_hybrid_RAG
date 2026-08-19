import type { NextConfig } from "next";

// Backend URL from environment variable
// Dev:        http://localhost:8000   (from .env.local)
// Production: https://cnpi-hybrid-rag-1.onrender.com  (from netlify.toml / Vercel env)
const BACKEND_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const nextConfig: NextConfig = {
  async redirects() {
    return [
      // /admin-panel  →  backend admin panel login page
      {
        source: "/admin-panel",
        destination: `${BACKEND_URL}/admin-panel/login/`,
        permanent: false, // 307 Temporary – survives backend URL changes
        basePath: false,
      },
      // /admin-panel/ (trailing slash) →  same
      {
        source: "/admin-panel/",
        destination: `${BACKEND_URL}/admin-panel/login/`,
        permanent: false,
        basePath: false,
      },
    ];
  },

  async rewrites() {
    return [
      // Proxy /api/* → Django /api/*  (chat endpoint only)
      {
        source: "/api/:path*",
        destination: `${BACKEND_URL}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
