import Link from "next/link";
import { AdminAssignmentImportView } from "@/components/admin-assignment-import-view";

export default function AdminAssignmentsPage() {
  // /admin配下は apps/web/src/app/(app)/admin/layout.tsx で
  // 認証・admin権限を既にチェック済み。
  return (
    <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-4 p-4">
      <Link
        href="/admin"
        className="self-start text-sm underline hover:opacity-70"
      >
        ← 管理者メニューに戻る
      </Link>
      <h1 className="text-xl font-semibold">配属結果インポート</h1>
      <AdminAssignmentImportView />
    </main>
  );
}
