import type { Session } from "next-auth";

// apiFetch/serverApiFetch共通。session.accessToken(RS256)をAuthorization: Bearerで付与する。
export function withAuthHeaders(
  session: Session | null,
  init: RequestInit,
): RequestInit {
  const headers = new Headers(init.headers);
  if (session?.accessToken) {
    headers.set("Authorization", `Bearer ${session.accessToken}`);
  }
  return { ...init, headers };
}
