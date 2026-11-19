import type { NextConfig } from "next";
import path from "path";

const BACKEND_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  turbopack: {
    // Point to this package's directory so Turbopack doesn't pick up
    // the parent G:\CNPI_Hybrid_RAG\package-lock.json as workspace root
    root: path.resolve(__dirname),
  },

  async redirects() {
    return [
      {
        source: "/admin-panel",
        destination: `${BACKEND_URL}/admin-panel/login/`,
        permanent: false,
        basePath: false,
      },
      {
        source: "/admin-panel/",
        destination: `${BACKEND_URL}/admin-panel/login/`,
        permanent: false,
        basePath: false,
      },
    ];
  },
};

export default nextConfig;
