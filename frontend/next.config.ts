import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // Standalone output keeps the production Docker image small (see Dockerfile).
  output: "standalone",
  images: {
    // Evidence screenshots/videos are served from presigned MinIO URLs whose
    // host varies by deployment, so we allow any https host rather than
    // hardcoding one here.
    remotePatterns: [{ protocol: "https", hostname: "**" }, { protocol: "http", hostname: "**" }],
  },
};

export default nextConfig;
