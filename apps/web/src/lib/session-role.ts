import "server-only";
import { cache } from "react";
import { auth } from "@/auth";
import { serverApiFetch } from "./api-server";

// メニューバーの管理者項目表示、/admin配下のアクセス制御の両方で
// 「本当にadminロールか」の判定を一箇所にまとめる(判定基準がずれると
// 見た目は管理者用メニューが出ないのにURLを直接踏むと入れてしまう、
// といった食い違いが起きるため)。React.cacheで包み、(app)/layout.tsxと
// admin/layout.tsxの両方から呼ばれても同一リクエスト内では/meへの問い合わせを
// 1回にまとめる。
export const getSessionRole = cache(async (): Promise<string | null> => {
  const session = await auth();
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
});
