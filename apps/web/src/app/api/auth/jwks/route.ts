import { getPublicJwks } from "@/lib/access-token";

// 秘密鍵は実行時のenvから読むため、ビルド時に静的化せず毎リクエスト実行する。
export const dynamic = "force-dynamic";

export function GET() {
  return Response.json(getPublicJwks());
}
