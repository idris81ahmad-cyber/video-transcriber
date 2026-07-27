import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Allow larger media uploads for transcription
  experimental: {
    serverActions: {
      bodySizeLimit: "25mb",
    },
  },
};

export default nextConfig;
