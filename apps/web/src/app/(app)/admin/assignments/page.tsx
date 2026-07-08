import Link from "next/link";
import { auth } from "@/auth";
import {
  AdminAssignmentImportView,
  type AdminTermOption,
} from "@/components/admin-assignment-import-view";
import { serverApiFetch } from "@/lib/api-server";
import type { Session } from "next-auth";

async function getTerms(session: Session | null): Promise<AdminTermOption[]> {
  try {
    const res = await serverApiFetch("/admin/recruitment-terms", session, {
      cache: "no-store",
    });
    if (!res.ok) {
      return [];
    }
    return (await res.json()) as AdminTermOption[];
  } catch {
    return [];
  }
}

export default async function AdminAssignmentsPage() {
  // /admin配下は apps/web/src/app/(app)/admin/layout.tsx で
  // 認証・admin権限を既にチェック済み。
  const session = await auth();
  const terms = await getTerms(session);

  return (
    <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-4 p-4">
      <Link
        href="/admin"
        className="self-start text-sm underline hover:opacity-70"
      >
        ← 管理者メニューに戻る
      </Link>
      <h1 className="text-xl font-semibold">配属結果インポート</h1>
      <AdminAssignmentImportView terms={terms} />
    </main>
  );
}
