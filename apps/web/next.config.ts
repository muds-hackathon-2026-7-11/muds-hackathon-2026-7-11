import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // 本番(spark)ではnginxがこのコンテナの公開ポートしか転送してこないため、
  // apiコンテナはホストへ公開しない。ブラウザからのAPI呼び出し(NEXT_PUBLIC_API_URL=/backend)を
  // ここでDocker内部の api:8000 へ中継する。API_BASE_URL未設定(ローカルdev等)なら何もしない。
  async rewrites() {
    const apiBaseUrl = process.env.API_BASE_URL;
    if (!apiBaseUrl) {
      return [];
    }
    return [
      {
        source: "/backend/:path*",
        destination: `${apiBaseUrl}/:path*`,
      },
    ];
  },
};

export default nextConfig;
