import type { Session } from "next-auth";

// バックエンド(FastAPI)呼び出しの共通ヘルパー。
// session.accessToken(RS256) を Authorization: Bearer で付与する。
//
// NEXT_PUBLIC_ 接頭辞の環境変数はNext.jsのビルド時に値が固定されるため、
// サーバー専用のURL(Docker内部ホスト名)にNEXT_PUBLIC_を使うとprodビルドで
// 壊れる(#42)。ブラウザ向け(apiFetch)とサーバー向け(serverApiFetch)で
// 環境変数と関数を分け、呼び出し元を間違えにくくする。
const BROWSER_API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8100";

function withAuthHeaders(
  session: Session | null,
  init: RequestInit,
): RequestInit {
  const headers = new Headers(init.headers);
  if (session?.accessToken) {
    headers.set("Authorization", `Bearer ${session.accessToken}`);
  }
  return { ...init, headers };
}

/** クライアントコンポーネントから呼ぶ。ブラウザから到達できるAPI URLを使う。 */
export async function apiFetch(
  path: string,
  session: Session | null,
  init: RequestInit = {},
): Promise<Response> {
  return fetch(`${BROWSER_API_URL}${path}`, withAuthHeaders(session, init));
}

/** サーバーコンポーネント/Route Handler/Server Actionから呼ぶ。Docker内部URLを使う。 */
export async function serverApiFetch(
  path: string,
  session: Session | null,
  init: RequestInit = {},
): Promise<Response> {
  const serverApiUrl = process.env.API_BASE_URL ?? "http://localhost:8100";
  return fetch(`${serverApiUrl}${path}`, withAuthHeaders(session, init));
}
