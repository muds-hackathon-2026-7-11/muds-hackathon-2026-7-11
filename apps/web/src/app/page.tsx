import Link from "next/link";
import { ProfileCard } from "@/components/profile-card";

type Me = {
  name: string;
  student_id: string | null;
  grade: string | null;
  research_theme: string | null;
};

// ログイン機能の実装後、false にすれば GET /me の実データ表示に戻る。
const USE_MOCK_PROFILE = true;

const MOCK_ME: Me = {
  name: "山田 太郎",
  student_id: "s2300000",
  grade: "B3",
  research_theme:
    "音声処理とLLMを組み合わせた誤り訂正システムの研究に関心があります。",
};

async function getMe(): Promise<Me | null> {
  try {
    const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/me`, {
      cache: "no-store",
    });
    if (!res.ok) {
      return null;
    }
    return (await res.json()) as Me;
  } catch {
    return null;
  }
}

export default async function Home() {
  const me = USE_MOCK_PROFILE ? MOCK_ME : await getMe();

  return (
    <main className="mx-auto flex w-full max-w-5xl flex-1 flex-col gap-4 p-4 sm:flex-row sm:items-start">
      <div className="sm:flex-1">
        {me ? (
          <ProfileCard
            name={me.name}
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
