import { auth } from "@/auth";
import {
  TeacherUnsubmittedView,
  type UnsubmittedApplicant,
} from "@/components/teacher-unsubmitted-view";
import { serverApiFetch } from "@/lib/api-server";
import type { Session } from "next-auth";

async function getUnsubmittedApplicants(
  session: Session | null,
): Promise<UnsubmittedApplicant[] | null> {
  try {
    const res = await serverApiFetch("/teacher/unsubmitted-applicants", session, {
      cache: "no-store",
    });
    if (!res.ok) {
      return null;
    }
    return (await res.json()) as UnsubmittedApplicant[];
  } catch {
    return null;
  }
}

export default async function UnsubmittedPage() {
  // apps/web/src/app/(app)/unsubmitted/layout.tsx で
  // 認証・teacher/admin権限を既にチェック済み。
  const session = await auth();
  const applicants = await getUnsubmittedApplicants(session);

  return (
    <main className="page-canvas relative flex flex-1 flex-col">
      <div className="mx-auto flex w-full max-w-4xl flex-1 flex-col gap-4 p-4 sm:p-6">
        <div>
          <h1 className="text-xl font-semibold text-zinc-900">未提出者一覧</h1>
          <p className="mt-2 text-sm text-zinc-500">
            今回の募集期間で志望理由をまだ提出していない学生を確認できます。
          </p>
        </div>

        {applicants === null ? (
          <section className="rounded-2xl border-2 border-red-300 bg-white p-6 text-sm text-red-600 shadow-sm">
            未提出者情報を取得できませんでした。時間をおいて再度お試しください。
          </section>
        ) : (
          <TeacherUnsubmittedView applicants={applicants} />
        )}
      </div>
    </main>
  );
}
