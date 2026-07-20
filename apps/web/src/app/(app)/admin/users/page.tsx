import Link from "next/link";
import { AdminUsersImportView } from "@/components/admin-users-import-view";

export default function AdminUsersPage() {
  // /admin配下は apps/web/src/app/(app)/admin/layout.tsx で
  // 認証・admin権限を既にチェック済み。
  return (
    <main className="page-canvas relative flex flex-1 flex-col">
      <div className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-4 p-4 sm:p-6">
        <Link
          href="/admin"
          className="self-start text-sm text-zinc-900 underline decoration-[#add8e6] underline-offset-2 hover:opacity-70"
        >
          ← 管理者メニューに戻る
        </Link>
        <h1 className="text-xl font-semibold text-zinc-900">
          学生名簿インポート
        </h1>
        <AdminUsersImportView />
      </div>
    </main>
  );
}
