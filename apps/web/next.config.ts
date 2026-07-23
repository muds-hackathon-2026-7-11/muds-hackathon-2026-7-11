import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // 本番(spark)ではnginxがこのコンテナの公開ポートしか転送してこないため、
  // apiコンテナはホストへ公開しない。ブラウザからのAPI呼び出し(NEXT_PUBLIC_API_URL=/backend)を
  // ここでDocker内部の api:8000 へ中継する。
  //
  // 値は環境変数にせず決め打ちにしている: rewrites()はnext build時(=Dockerイメージの
  // ビルド時)に1回だけ評価されビルド成果物に焼き込まれるため、コンテナ起動時に渡す
  // env_fileの値(process.env.API_BASE_URL)はここでは読めない(ビルドとコンテナ起動は
  // 別フェーズで、docker composeのenv_fileはビルドに渡らない)。api:8000はdev/prod問わず
  // Docker内部のサービス名解決で常に同じ値なので、決め打ちで問題ない。
  async rewrites() {
    return [
      {
        source: "/backend/:path*",
        destination: "http://api:8000/:path*",
      },
    ];
  },
};

export default nextConfig;
