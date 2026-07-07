import "server-only";
import type { Session } from "next-auth";
import { serverApiFetch } from "./api-server";

// メニューバーの管理者項目表示、/admin配下のアクセス制御の両方で
// 「本当にadminロールか」の判定を一箇所にまとめる(判定基準がずれると
// 見た目は管理者用メニューが出ないのにURLを直接踏むと入れてしまう、
// といった食い違いが起きるため)。
export async function getSessionRole(
  session: Session | null,
): Promise<string | null> {
  if (!session) {
    return null;
  }
  try {
    const res = await serverApiFetch("/me", session, { cache: "no-store" });
    if (!res.ok) {
      return null;
    }
    const me = (await res.json()) as { role: string };
    return me.role;
  } catch {
    return null;
  }
}
