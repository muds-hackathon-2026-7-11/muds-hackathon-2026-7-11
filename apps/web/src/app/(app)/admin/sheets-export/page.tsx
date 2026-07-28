import Link from "next/link";
import { auth } from "@/auth";
import { AdminSheetsExportView } from "@/components/admin-sheets-export-view";
import { serverApiFetch } from "@/lib/api-server";
import type { Session } from "next-auth";

async function getExportKey(session: Session | null): Promise<string | null> {
  try {
    const res = await serverApiFetch("/admin/sheets-export-key", session, {
      cache: "no-store",
    });
    if (!res.ok) {
      return null;
    }
    const data = (await res.json()) as { key: string | null };
    return data.key;
  } catch {
    return null;
  }
}

export default async function AdminSheetsExportPage() {
  // /admin配下は apps/web/src/app/(app)/admin/layout.tsx で
  // 認証・admin権限を既にチェック済み。
  const session = await auth();
  const exportKey = await getExportKey(session);

  return (
    <main className="page-canvas relative flex flex-1 flex-col">
      <div className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-4 p-4 sm:p-6">
        <Link
          href="/admin"
          className="self-start text-sm text-zinc-500 underline decoration-[#add8e6] underline-offset-4 transition-colors hover:text-zinc-800"
        >
          ← 管理者メニューに戻る
        </Link>
        <div>
          <h1 className="text-xl font-semibold text-zinc-900">
            スプレッドシート連携
          </h1>
          <p className="mt-2 text-sm text-zinc-500">
            志望理由データをGoogleスプレッドシートへ自動反映するための設定。
          </p>
        </div>
        <AdminSheetsExportView initialKey={exportKey} />
      </div>
    </main>
  );
}
