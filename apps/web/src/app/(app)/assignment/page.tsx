import { redirect } from "next/navigation";
import { auth } from "@/auth";
import {
  SeminarStatsList,
  type SeminarStats,
} from "@/components/seminar-stats-list";
import { serverApiFetch } from "@/lib/api-server";
import type { Session } from "next-auth";

async function getSeminarStats(
  session: Session | null,
): Promise<SeminarStats[]> {
  try {
    const res = await serverApiFetch("/seminars/stats", session, {
      cache: "no-store",
    });
    if (!res.ok) {
      return [];
    }
    return (await res.json()) as SeminarStats[];
  } catch {
    return [];
  }
}

export default async function AssignmentPage() {
  const session = await auth();
  if (!session) {
    redirect("/login");
  }

  const stats = await getSeminarStats(session);

  return (
    <main className="relative flex flex-1 flex-col bg-[#e6e6e6]">
      <div className="relative mx-auto flex w-full max-w-7xl flex-1 flex-col gap-6 p-4 sm:p-6">
        <h1 className="text-2xl font-bold text-zinc-800">応募状況</h1>
        <SeminarStatsList stats={stats} />
      </div>
    </main>
  );
}
