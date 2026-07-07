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
    <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-4 p-4">
      {result.status === "error" ? (
        <p className="text-foreground/60">
          ゼミ情報を取得できませんでした。時間をおいて再度お試しください。
        </p>
      ) : (
        <SeminarDetailView seminar={result.seminar} />
      )}
    </main>
  );
}
