import type { NextConfig } from "next";

const apiProxyTarget = (process.env.HIFY_API_PROXY_TARGET ?? "http://127.0.0.1:8000").replace(
  /\/+$/,
  "",
);

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${apiProxyTarget}/:path*`,
      },
    ];
  },
};

export default nextConfig;
