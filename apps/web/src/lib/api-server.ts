import "server-only";
import type { Session } from "next-auth";
import { withAuthHeaders } from "./api-headers";

// サーバーコンポーネント/Route Handler/Server Action専用(#42)。Docker内部URLを使う。
// クライアントコンポーネントからはこのファイルではなく api-client.ts の apiFetch を
// 使うこと(誤って読み込むとビルドエラーになる)。
export async function serverApiFetch(
  path: string,
  session: Session | null,
  init: RequestInit = {},
): Promise<Response> {
  const serverApiUrl = process.env.API_BASE_URL ?? "http://localhost:8100";
  return fetch(`${serverApiUrl}${path}`, withAuthHeaders(session, init));
}
