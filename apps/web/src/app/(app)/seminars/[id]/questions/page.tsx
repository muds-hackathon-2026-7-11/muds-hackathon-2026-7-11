import Link from "next/link";
import { notFound, redirect } from "next/navigation";
import { auth } from "@/auth";
import { FaqList, type Question } from "@/components/faq-list";
import { serverApiFetch } from "@/lib/api-server";
import type { Session } from "next-auth";

type QuestionsResult =
  | { status: "ok"; questions: Question[] }
  | { status: "not_found" }
  | { status: "error" };

async function getQuestions(
  session: Session | null,
  seminarId: string,
): Promise<QuestionsResult> {
  try {
    const res = await serverApiFetch(
      `/questions?seminar_id=${seminarId}`,
      session,
      { cache: "no-store" },
    );
    // 404(ゼミが存在しない)に加え、422(seminar_idがUUID形式でない=不正な
    // URL)も「見つからない」として扱う。どちらもこのURLに対応する有効な
    // ゼミが無いという意味では同じであり、一時的な失敗ではないため。
    if (res.status === 404 || res.status === 422) {
      return { status: "not_found" };
    }
    if (!res.ok) {
      return { status: "error" };
    }
    return { status: "ok", questions: (await res.json()) as Question[] };
  } catch {
    return { status: "error" };
  }
}

export default async function SeminarQuestionsPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const session = await auth();
  if (!session) {
    redirect("/login");
  }

  const { id } = await params;
  const result = await getQuestions(session, id);

  if (result.status === "not_found") {
    notFound();
  }

  return (
    <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-4 p-4">
      <Link
        href={`/seminars/${id}`}
        className="self-start text-sm underline hover:opacity-70"
      >
        ← ゼミ詳細に戻る
      </Link>

      <h1 className="text-xl font-semibold">FAQ</h1>

      {result.status === "error" ? (
        <p className="text-foreground/60">
          質問一覧を取得できませんでした。時間をおいて再度お試しください。
        </p>
      ) : (
        <FaqList questions={result.questions} />
      )}
    </main>
  );
}
