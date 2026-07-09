import { auth } from "@/auth";
import {
  TeacherApplicantsView,
  type SeminarApplicants,
} from "@/components/teacher-applicants-view";
import { serverApiFetch } from "@/lib/api-server";
import type { Session } from "next-auth";

async function getApplicants(
  session: Session | null,
): Promise<SeminarApplicants[] | null> {
  try {
    const res = await serverApiFetch("/teacher/applicants", session, {
      cache: "no-store",
    });
    if (!res.ok) {
      return null;
    }
    return (await res.json()) as SeminarApplicants[];
  } catch {
    return null;
  }
}

export default async function TeacherApplicantsPage() {
  // /teacher配下は apps/web/src/app/(app)/teacher/layout.tsx で
  // 認証・teacher権限を既にチェック済み。
  const session = await auth();
  const applicants = await getApplicants(session);

  return (
    <main className="page-canvas relative flex flex-1 flex-col">
      <div className="mx-auto flex w-full max-w-4xl flex-1 flex-col gap-4 p-4 sm:p-6">
        <div>
          <h1 className="text-xl font-semibold text-zinc-900">応募者一覧</h1>
          <p className="mt-2 text-sm text-zinc-500">
            担当ゼミへの応募者を志望順位別に確認できます。
          </p>
        </div>

        {applicants === null ? (
          <section className="rounded-2xl border-2 border-red-300 bg-white p-6 text-sm text-red-600 shadow-sm">
            応募者情報を取得できませんでした。時間をおいて再度お試しください。
          </section>
        ) : (
          <TeacherApplicantsView initialData={applicants} />
        )}
      </div>
    </main>
  );
}
