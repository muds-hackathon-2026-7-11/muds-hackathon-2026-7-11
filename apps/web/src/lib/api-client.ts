import "client-only";
import type { Session } from "next-auth";
import { withAuthHeaders } from "./api-headers";

// クライアントコンポーネント専用(#42)。ブラウザから到達できるAPI URLを使う。
// NEXT_PUBLIC_ 接頭辞の環境変数はNext.jsのビルド時に値が固定される仕様のため、
// サーバー専用のURL(Docker内部ホスト名)にここを使うとprodビルドで壊れる。
// サーバー側からはこのファイルではなく api-server.ts の serverApiFetch を使うこと
// (誤って読み込むとビルドエラーになる)。
const BROWSER_API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8100";

export async function apiFetch(
  path: string,
  session: Session | null,
  init: RequestInit = {},
): Promise<Response> {
  return fetch(`${BROWSER_API_URL}${path}`, withAuthHeaders(session, init));
}
