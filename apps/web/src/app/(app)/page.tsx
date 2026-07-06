import Link from "next/link";
import { redirect } from "next/navigation";
import { auth } from "@/auth";
import { LogoutButton } from "@/components/logout-button";
import { ProfileCard } from "@/components/profile-card";
import { serverApiFetch } from "@/lib/api-server";
import type { Session } from "next-auth";

type Me = {
  name: string;
  email: string;
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
  if (!session) {
    redirect("/login");
  }
  const me = await getMe(session);

  return (
    <main className="relative flex flex-1 flex-col overflow-hidden">
      {/* ログイン画面と同じ外周ビネット。縁を黒くぼかして中央を引き立てる。 */}
      <div aria-hidden className="vignette pointer-events-none absolute inset-0" />

      <div className="relative mx-auto flex w-full max-w-5xl flex-1 flex-col gap-6 p-4 sm:p-6">
        <div className="flex items-center justify-between">
          <h1 className="font-brand text-3xl font-bold tracking-tight text-zinc-900 drop-shadow-sm sm:text-4xl dark:text-zinc-50">
            マイページ
          </h1>
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
              />
            ) : (
              <section className="rounded-2xl border border-white/60 bg-white/80 p-6 text-foreground/60 shadow-lg shadow-zinc-900/10 backdrop-blur-sm dark:border-white/10 dark:bg-zinc-900/70">
                プロフィールを取得できませんでした。
              </section>
            )}
          </div>

          <div className="flex flex-col gap-6 sm:w-72">
            <section className="rounded-2xl border border-white/60 bg-white/80 p-6 shadow-lg shadow-zinc-900/10 backdrop-blur-sm dark:border-white/10 dark:bg-zinc-900/70">
              <p className="text-sm text-foreground/60">所属ゼミ</p>
              <p className="mt-1 font-semibold">準備中</p>
            </section>

            <section className="rounded-2xl border border-white/60 bg-white/80 p-6 shadow-lg shadow-zinc-900/10 backdrop-blur-sm dark:border-white/10 dark:bg-zinc-900/70">
              <p className="text-sm text-foreground/60">志望提出状況</p>
              <p className="mt-1 font-semibold">準備中</p>
              <div className="mt-4">
                <Link
                  href="/apply"
                  className="block rounded-md bg-zinc-900 px-4 py-2 text-center text-sm font-medium text-white shadow-lg shadow-zinc-900/30 transition-all hover:translate-y-0.5 hover:bg-zinc-700 hover:shadow-md hover:shadow-zinc-900/20 active:translate-y-1 active:shadow-sm focus:outline-none focus-visible:ring-4 focus-visible:ring-zinc-500 dark:bg-white dark:text-zinc-900 dark:shadow-white/20 dark:hover:bg-zinc-200"
                >
                  志望を提出
                </Link>
              </div>
            </section>
          </div>
        </div>
      </div>
    </main>
  );
}
