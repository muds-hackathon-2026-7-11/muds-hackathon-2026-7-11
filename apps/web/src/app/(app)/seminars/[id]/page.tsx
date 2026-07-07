import { notFound, redirect } from "next/navigation";
import { auth } from "@/auth";
import {
  SeminarDetailView,
  type SeminarDetail,
} from "@/components/seminar-detail";
import { serverApiFetch } from "@/lib/api-server";
import type { Session } from "next-auth";

type SeminarResult =
  | { status: "ok"; seminar: SeminarDetail }
  | { status: "not_found" }
  | { status: "error" };

async function getSeminar(
  session: Session | null,
  id: string,
): Promise<SeminarResult> {
  try {
    const res = await serverApiFetch(`/seminars/${id}`, session, {
      cache: "no-store",
    });
    if (res.status === 404) {
      return { status: "not_found" };
    }
    if (!res.ok) {
      return { status: "error" };
    }
    return { status: "ok", seminar: (await res.json()) as SeminarDetail };
  } catch {
    return { status: "error" };
  }
}

export default async function SeminarDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const session = await auth();
  if (!session) {
    redirect("/login");
  }

  const { id } = await params;
  const result = await getSeminar(session, id);

  if (result.status === "not_found") {
    notFound();
  }

  return (
    <main className="relative flex flex-1 flex-col bg-[#e6e6e6]">
      <div className="relative mx-auto flex w-full max-w-3xl flex-1 flex-col gap-6 p-4 sm:p-6">
        {result.status === "error" ? (
          <section className="rounded-2xl border-2 border-[#add8e6] bg-white p-6 text-zinc-500 shadow-sm shadow-[#add8e6]/30">
            ゼミ情報を取得できませんでした。時間をおいて再度お試しください。
          </section>
        ) : (
          <SeminarDetailView seminar={result.seminar} />
        )}
      </div>
    </main>
  );
}
