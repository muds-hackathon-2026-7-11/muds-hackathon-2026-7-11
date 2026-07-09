import { auth } from "@/auth";
import {
  TeacherSeminarView,
  type TeacherSeminar,
} from "@/components/teacher-seminar-view";
import { serverApiFetch } from "@/lib/api-server";
import type { Session } from "next-auth";

async function getOwnSeminars(
  session: Session | null,
): Promise<TeacherSeminar[] | null> {
  try {
    const res = await serverApiFetch("/teacher/seminars", session, {
      cache: "no-store",
    });
    if (!res.ok) {
      return null;
    }
    return (await res.json()) as TeacherSeminar[];
  } catch {
    return null;
  }
}

export default async function TeacherSeminarPage() {
  // /teacher配下は apps/web/src/app/(app)/teacher/layout.tsx で
  // 認証・teacher権限を既にチェック済み。
  const session = await auth();
  const seminars = await getOwnSeminars(session);

  return (
    <main className="page-canvas relative flex flex-1 flex-col">
      <div className="mx-auto flex w-full max-w-4xl flex-1 flex-col gap-4 p-4 sm:p-6">
        <div>
          <h1 className="text-xl font-semibold text-zinc-900">ゼミ設定</h1>
          <p className="mt-2 text-sm text-zinc-500">
            担当ゼミの紹介文・写真・紹介資料を編集できます。
          </p>
        </div>

        {seminars === null ? (
          <section className="rounded-2xl border-2 border-red-300 bg-white p-6 text-sm text-red-600 shadow-sm">
            ゼミ情報を取得できませんでした。時間をおいて再度お試しください。
          </section>
        ) : (
          <TeacherSeminarView initialSeminars={seminars} />
        )}
      </div>
    </main>
  );
}
