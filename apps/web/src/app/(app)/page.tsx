import Link from "next/link";
import { redirect } from "next/navigation";
import { auth } from "@/auth";
import { LogoutButton } from "@/components/logout-button";
import { ProfileCard, type ResearchTag } from "@/components/profile-card";
import { serverApiFetch } from "@/lib/api-server";
import type { Session } from "next-auth";

type Me = {
  name: string;
  email: string;
  grade: string | null;
  research_theme: string | null;
  interest_tags: ResearchTag[];
};

async function getMe(session: Session | null): Promise<Me | null> {
  try {
    const res = await serverApiFetch("/me", session, { cache: "no-store" });
    if (!res.ok) {
      return null;
    }
    return (await res.json()) as Me;
  } catch {
    return null;
  }
}

async function getResearchTags(
  session: Session | null,
): Promise<ResearchTag[]> {
  try {
    const res = await serverApiFetch("/research-tags", session, {
      cache: "no-store",
    });
    if (!res.ok) {
      return [];
    }
    return (await res.json()) as ResearchTag[];
  } catch {
    return [];
  }
}

export default async function Home() {
  const session = await auth();
  if (!session) {
    redirect("/login");
  }
  const [me, researchTags] = await Promise.all([
    getMe(session),
    getResearchTags(session),
  ]);

  return (
    <main className="page-canvas relative flex flex-1 flex-col">
      <div className="relative mx-auto flex w-full max-w-5xl flex-1 flex-col gap-6 p-4 sm:p-6">
        <div className="flex justify-end">
          <LogoutButton />
        </div>

        <div className="flex flex-col gap-6 sm:flex-row sm:items-start">
          <div className="sm:flex-1">
            {me ? (
              <ProfileCard
                name={me.name}
                email={me.email}
                grade={me.grade}
                researchTheme={me.research_theme}
                interestTags={me.interest_tags}
                allTags={researchTags}
              />
            ) : (
              <section className="rounded-2xl border-2 border-[#add8e6] bg-white p-6 text-zinc-500 shadow-sm shadow-[#add8e6]/30">
                プロフィールを取得できませんでした。
              </section>
            )}
          </div>

          <div className="flex flex-col gap-6 sm:w-72">
            <section className="rounded-2xl border-2 border-[#add8e6] bg-white p-6 shadow-sm shadow-[#add8e6]/30">
              <p className="text-xs font-semibold uppercase tracking-wider text-zinc-400">
                Current Assignment
              </p>
              <p className="mt-2 text-xs text-zinc-400">所属ゼミ</p>
              <p className="mt-0.5 text-lg font-semibold text-zinc-800">
                準備中
              </p>
            </section>

            <section className="rounded-2xl border-2 border-[#add8e6] bg-white p-6 shadow-sm shadow-[#add8e6]/30">
              <p className="text-xs font-semibold uppercase tracking-wider text-zinc-400">
                Application Status
              </p>
              <p className="mt-2 text-xs text-zinc-400">志望提出状況</p>
              <p className="mt-0.5 text-lg font-semibold text-zinc-800">
                準備中
              </p>
              <div className="mt-4">
                <Link
                  href="/apply"
                  className="flex items-center justify-center gap-2 rounded-full bg-[#add8e6] px-4 py-2.5 text-center text-sm font-semibold text-sky-950 shadow-sm transition-all hover:bg-[#9bcfe0] hover:shadow active:translate-y-px focus:outline-none focus-visible:ring-4 focus-visible:ring-[#add8e6]/50"
                >
                  志望を提出
                  <span aria-hidden>›</span>
                </Link>
              </div>
            </section>
          </div>
        </div>
      </div>
    </main>
  );
}
