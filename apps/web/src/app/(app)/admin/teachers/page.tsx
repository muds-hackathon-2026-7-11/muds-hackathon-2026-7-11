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
            教員・管理者管理
          </h1>
          <p className="mt-2 text-sm text-zinc-500">
            教員は研究情報を含めて管理し、管理者はログイン権限のみの独立したユーザーとして管理します。
          </p>
        </div>
        <AdminPeopleTabs initialTeachers={teachers} initialAdmins={admins} />
      </div>
    </main>
  );
}
