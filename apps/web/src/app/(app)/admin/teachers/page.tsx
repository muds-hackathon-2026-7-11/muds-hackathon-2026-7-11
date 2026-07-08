import Link from "next/link";
import { auth } from "@/auth";
import {
  AdminTeachersView,
  type AdminTeacher,
} from "@/components/admin-teachers-view";
import { serverApiFetch } from "@/lib/api-server";
import type { Session } from "next-auth";

async function getTeachers(session: Session | null): Promise<AdminTeacher[]> {
  try {
    const res = await serverApiFetch("/admin/teachers", session, {
      cache: "no-store",
    });
    if (!res.ok) {
      return [];
    }
    return (await res.json()) as AdminTeacher[];
  } catch {
    return [];
  }
}

export default async function AdminTeachersPage() {
  // /admin配下は apps/web/src/app/(app)/admin/layout.tsx で
  // 認証・admin権限を既にチェック済み。
  const session = await auth();
  const teachers = await getTeachers(session);

  return (
    <main className="page-canvas relative flex flex-1 flex-col">
      <div className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-4 p-4 sm:p-6">
        <Link
          href="/admin"
          className="self-start text-sm text-zinc-500 underline decoration-[#add8e6] underline-offset-4 transition-colors hover:text-zinc-800"
        >
          ← 管理者メニューに戻る
        </Link>
        <h1 className="text-xl font-semibold text-zinc-900">教員管理</h1>
        <p className="text-sm text-zinc-500">
          新規の教員追加はCSVインポートで行います。ここでは既存教員の編集のみ行えます。
        </p>
        <AdminTeachersView initialTeachers={teachers} />
      </div>
    </main>
  );
}
