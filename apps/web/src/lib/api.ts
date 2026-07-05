import type { Session } from "next-auth";

// バックエンド(FastAPI)呼び出しの共通ヘルパー。
// session.accessToken(RS256) を Authorization: Bearer で付与する。
// ※ブラウザからの呼び出しはバックエンド側のCORS対応(別Issue)が前提。
const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8100";

export async function apiFetch(
  path: string,
  session: Session | null,
  init: RequestInit = {},
): Promise<Response> {
  const headers = new Headers(init.headers);
  if (session?.accessToken) {
    headers.set("Authorization", `Bearer ${session.accessToken}`);
  }
  return fetch(`${API_URL}${path}`, { ...init, headers });
}
