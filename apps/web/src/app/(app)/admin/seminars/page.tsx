import Link from "next/link";
import { auth } from "@/auth";
import {
  AdminSeminarsView,
  type AdminRecruitmentTerm,
  type AdminSeminar,
  type AdminSeminarRecruitment,
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

// 募集人数は募集ラウンド(recruitment_terms)単位で設定するため、
// どのラウンド向けの設定かをまず決める必要がある。募集ラウンド管理画面
// (別イシュー)がまだ無いため、ここでは一覧の先頭(academic_year降順)=
// 直近に作られたラウンドを「現在設定対象のラウンド」として扱う。
async function getLatestTerm(
  session: Session | null,
): Promise<AdminRecruitmentTerm | null> {
  try {
    const res = await serverApiFetch("/admin/recruitment-terms", session, {
      cache: "no-store",
    });
    if (!res.ok) {
      return null;
    }
    const terms = (await res.json()) as AdminRecruitmentTerm[];
    return terms[0] ?? null;
  } catch {
    return null;
  }
}

async function getRecruitments(
  session: Session | null,
  termId: string,
): Promise<AdminSeminarRecruitment[]> {
  try {
    const res = await serverApiFetch(
      `/admin/recruitment-terms/${termId}/seminars`,
      session,
      { cache: "no-store" },
    );
    if (!res.ok) {
      return [];
    }
    return (await res.json()) as AdminSeminarRecruitment[];
  } catch {
    return [];
  }
}

export default async function AdminSeminarsPage() {
  // /admin配下は apps/web/src/app/(app)/admin/layout.tsx で
  // 認証・admin権限を既にチェック済み。
  const session = await auth();

  const [seminars, teachers, latestTerm] = await Promise.all([
    getSeminars(session),
    getTeachers(session),
    getLatestTerm(session),
  ]);
  const recruitments = latestTerm
    ? await getRecruitments(session, latestTerm.id)
    : [];

  return (
    <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-4 p-4">
      <Link
        href="/admin"
        className="self-start text-sm underline hover:opacity-70"
      >
        ← 管理者メニューに戻る
      </Link>
      <h1 className="text-xl font-semibold">ゼミ管理</h1>
      <AdminSeminarsView
        initialSeminars={seminars}
        teacherOptions={teachers}
        latestTerm={latestTerm}
        recruitments={recruitments}
      />
    </main>
  );
}
