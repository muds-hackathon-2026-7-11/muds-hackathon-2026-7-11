import Link from "next/link";
import { auth } from "@/auth";
import type { AdminUser } from "@/components/admin-admins-view";
import { AdminPeopleTabs } from "@/components/admin-people-tabs";
import type { AdminTeacher } from "@/components/admin-teachers-view";
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

async function getAdmins(session: Session | null): Promise<AdminUser[]> {
  try {
    const res = await serverApiFetch("/admin/admins", session, {
      cache: "no-store",
    });
    if (!res.ok) {
      return [];
    }
    return (await res.json()) as AdminUser[];
  } catch {
    return [];
  }
}

export default async function AdminTeachersPage() {
  // /admin配下は apps/web/src/app/(app)/admin/layout.tsx で
  // 認証・admin権限を既にチェック済み。
  const session = await auth();
  const [teachers, admins] = await Promise.all([
    getTeachers(session),
    getAdmins(session),
  ]);

  return (
    <main className="relative flex flex-1 flex-col bg-[#e6e6e6]">
      <div className="relative mx-auto flex w-full max-w-3xl flex-1 flex-col gap-6 p-4 sm:p-6">
        <Link
          href="/admin"
          className="self-start text-sm text-zinc-900 underline decoration-[#add8e6] underline-offset-2 hover:opacity-70"
        >
          ← 管理者メニューに戻る
        </Link>
        <div>
          <h1 className="text-2xl font-bold text-zinc-900">教員・管理者管理</h1>
          <p className="mt-2 text-sm text-zinc-700">
            教員は研究情報を含めて管理し、管理者はログイン権限のみの独立したユーザーとして管理します。
          </p>
        </div>
        <AdminPeopleTabs initialTeachers={teachers} initialAdmins={admins} />
      </div>
    </main>
  );
}
