import Link from "next/link";
import { redirect } from "next/navigation";
import { auth } from "@/auth";
import { ProfileCard, type ResearchTag } from "@/components/profile-card";
import { serverApiFetch } from "@/lib/api-server";
import type { Session } from "next-auth";

type CurrentSeminar = {
  id: string;
  name: string;
};

type Me = {
  name: string;
  email: string;
  grade: string | null;
  research_title: string | null;
  research_theme: string | null;
  interest_tags: ResearchTag[];
  current_seminar: CurrentSeminar | null;
};

type MyApplication = {
  id: string | null;
  status: "draft" | "submitted";
  submitted_at: string | null;
  is_editable: boolean;
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

async function getMyApplication(
  session: Session | null,
): Promise<MyApplication | null> {
  try {
    const res = await serverApiFetch("/applications/me", session, {
      cache: "no-store",
    });
    if (!res.ok) {
      return null;
    }
    return (await res.json()) as MyApplication;
  } catch {
    return null;
  }
}

// #137: マイページの「Application Status」カードの文言・ボタンを、
// 実際の志望提出状況(募集期間外/未提出/下書き/提出済み)に応じて出し分ける。
function applicationStatusView(application: MyApplication | null): {
  label: string;
  buttonLabel: string | null;
} {
  if (application === null) {
    return { label: "取得できませんでした", buttonLabel: null };
  }
  if (!application.is_editable) {
    if (application.id === null) {
      // 現在募集中の期間が無く、過去の提出も無い(preparing/closed/未設定)。
      return { label: "準備中", buttonLabel: null };
    }
    return {
      label:
        application.status === "submitted" ? "提出済み(前回)" : "下書き(前回)",
      buttonLabel: "内容を確認",
    };
  }
  if (application.id === null) {
    return { label: "未提出", buttonLabel: "志望を提出" };
  }
  return {
    label: application.status === "submitted" ? "提出済み" : "下書き保存中",
    buttonLabel: "内容を編集",
  };
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
  const [me, researchTags, myApplication] = await Promise.all([
    getMe(session),
    getResearchTags(session),
    getMyApplication(session),
  ]);
  const applicationStatus = applicationStatusView(myApplication);

  return (
    <main className="page-canvas relative flex flex-1 flex-col">
      <div className="relative mx-auto flex w-full max-w-5xl flex-1 flex-col gap-6 p-4 sm:p-6">
        <div className="flex flex-col gap-6 sm:flex-row sm:items-start">
          <div className="sm:flex-1">
            {me ? (
              <ProfileCard
                name={me.name}
                email={me.email}
                grade={me.grade}
                researchTitle={me.research_title}
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
              <p className="mt-2 text-lg font-semibold text-zinc-800">
                {me?.current_seminar?.name ?? "未配属"}
              </p>
            </section>

            <section className="rounded-2xl border-2 border-[#add8e6] bg-white p-6 shadow-sm shadow-[#add8e6]/30">
              <p className="text-xs font-semibold uppercase tracking-wider text-zinc-400">
                Application Status
              </p>
              <p className="mt-2 text-lg font-semibold text-zinc-800">
                {applicationStatus.label}
              </p>
              {applicationStatus.buttonLabel && (
                <div className="mt-4">
                  <Link
                    href="/apply"
                    className="flex items-center justify-center gap-2 rounded-full bg-[#add8e6] px-4 py-2.5 text-center text-sm font-semibold text-sky-950 shadow-sm transition-all hover:bg-[#9bcfe0] hover:shadow active:translate-y-px focus:outline-none focus-visible:ring-4 focus-visible:ring-[#add8e6]/50"
                  >
                    {applicationStatus.buttonLabel}
                    <span aria-hidden>›</span>
                  </Link>
                </div>
              )}
            </section>
          </div>
        </div>
      </div>
    </main>
  );
}
