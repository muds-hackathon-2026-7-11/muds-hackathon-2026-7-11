import Link from "next/link";
import { auth } from "@/auth";
import { ProfileCard } from "@/components/profile-card";
import { serverApiFetch } from "@/lib/api-server";
import type { Session } from "next-auth";

type Me = {
  name: string;
  email: string;
  student_id: string | null;
  grade: string | null;
  research_theme: string | null;
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

export default async function Home() {
  const session = await auth();
  const me = await getMe(session);

  return (
    <main className="mx-auto flex w-full max-w-5xl flex-1 flex-col gap-4 p-4 sm:flex-row sm:items-start">
      <div className="sm:flex-1">
        {me ? (
          <ProfileCard
            name={me.name}
            email={me.email}
            studentId={me.student_id}
            grade={me.grade}
            researchTheme={me.research_theme}
          />
        ) : (
          <section className="rounded-lg border border-black/[.08] p-6 text-foreground/60 dark:border-white/[.145]">
            プロフィールを取得できませんでした。
          </section>
        )}
      </div>

      <div className="flex flex-col gap-4 sm:w-72">
        <section className="rounded-lg border border-black/[.08] p-6 dark:border-white/[.145]">
          <p className="text-sm text-foreground/60">所属ゼミ</p>
          <p className="mt-1 font-semibold">準備中</p>
        </section>

        <section className="rounded-lg border border-black/[.08] p-6 dark:border-white/[.145]">
          <p className="text-sm text-foreground/60">志望提出状況</p>
          <p className="mt-1 font-semibold">準備中</p>
          <div className="mt-4">
            <Link
              href="/apply"
              className="block rounded-full border border-black/[.08] px-4 py-2 text-center text-sm font-medium hover:bg-black/[.04] dark:border-white/[.145] dark:hover:bg-white/[.08]"
            >
              志望を提出
            </Link>
          </div>
        </section>
      </div>
    </main>
  );
}
