import Link from "next/link";
import { auth } from "@/auth";
import {
  AdminSeminarsView,
  type AdminSeminar,
  type AdminTeacherOption,
} from "@/components/admin-seminars-view";
import { serverApiFetch } from "@/lib/api-server";
import type { Session } from "next-auth";

async function getSeminars(session: Session | null): Promise<AdminSeminar[]> {
  try {
    const res = await serverApiFetch("/admin/seminars", session, {
      cache: "no-store",
    });
    if (!res.ok) {
      return [];
    }
    return (await res.json()) as AdminSeminar[];
  } catch {
    return [];
  }
}

async function getTeachers(
  session: Session | null,
): Promise<AdminTeacherOption[]> {
  try {
    const res = await serverApiFetch("/admin/teachers", session, {
      cache: "no-store",
    });
    if (!res.ok) {
      return [];
    }
    return (await res.json()) as AdminTeacherOption[];
  } catch {
    return [];
  }
}

export default async function AdminSeminarsPage() {
  // /admin配下は apps/web/src/app/(app)/admin/layout.tsx で
  // 認証・admin権限を既にチェック済み。
  const session = await auth();

  const [seminars, teachers] = await Promise.all([
    getSeminars(session),
    getTeachers(session),
  ]);

  return (
    <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-4 p-4">
      <Link
        href="/admin"
        className="self-start text-sm underline hover:opacity-70"
      >
        ← 管理者メニューに戻る
      </Link>
      <h1 className="text-xl font-semibold">ゼミ管理</h1>
      <AdminSeminarsView initialSeminars={seminars} teacherOptions={teachers} />
    </main>
  );
}
