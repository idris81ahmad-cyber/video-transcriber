import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Align with Vercel Hobby request body limits (~4.5 MB)
  experimental: {
    serverActions: {
      bodySizeLimit: "4.5mb",
    },
  },
};

export default nextConfig;
