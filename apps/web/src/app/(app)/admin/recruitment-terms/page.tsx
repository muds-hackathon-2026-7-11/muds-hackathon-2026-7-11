import Link from "next/link";
import { auth } from "@/auth";
import {
  AdminRecruitmentTermsView,
  summarizeTargetGrades,
  type AdminRecruitmentTerm,
  type AdminSeminarOption,
  type AdminSeminarRecruitment,
} from "@/components/admin-recruitment-terms-view";
import { serverApiFetch } from "@/lib/api-server";
import type { Session } from "next-auth";

type RecruitmentTermApiResponse = Omit<
  AdminRecruitmentTerm,
  "target_grades_summary"
>;

async function getTargetGradesSummary(
  session: Session | null,
  termId: string,
): Promise<string> {
  try {
    const res = await serverApiFetch(
      `/admin/recruitment-terms/${termId}/seminars`,
      session,
      { cache: "no-store" },
    );
    if (!res.ok) {
      return "取得できませんでした";
    }
    const recruitments = (await res.json()) as AdminSeminarRecruitment[];
    return summarizeTargetGrades(recruitments);
  } catch {
    return "取得できませんでした";
  }
}

async function getTerms(
  session: Session | null,
): Promise<AdminRecruitmentTerm[]> {
  try {
    const res = await serverApiFetch("/admin/recruitment-terms", session, {
      cache: "no-store",
    });
    if (!res.ok) {
      return [];
    }
    const terms = (await res.json()) as RecruitmentTermApiResponse[];
    // ラウンド一覧のカードに、ゼミ別設定を横断した対象学年の要約を
    // 直接表示する(「ゼミ別設定」を開かなくても確認できるように)。
    return Promise.all(
      terms.map(async (term) => ({
        ...term,
        target_grades_summary: await getTargetGradesSummary(session, term.id),
      })),
    );
  } catch {
    return [];
  }
}

async function getSeminars(
  session: Session | null,
): Promise<AdminSeminarOption[]> {
  try {
    const res = await serverApiFetch("/admin/seminars", session, {
      cache: "no-store",
    });
    if (!res.ok) {
      return [];
    }
    return (await res.json()) as AdminSeminarOption[];
  } catch {
    return [];
  }
}

export default async function AdminRecruitmentTermsPage() {
  // /admin配下は apps/web/src/app/(app)/admin/layout.tsx で
  // 認証・admin権限を既にチェック済み。
  const session = await auth();
  const [terms, seminars] = await Promise.all([
    getTerms(session),
    getSeminars(session),
  ]);

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
          募集ラウンド管理
        </h1>
        <AdminRecruitmentTermsView
          initialTerms={terms}
          allSeminars={seminars}
        />
      </div>
    </main>
  );
}
