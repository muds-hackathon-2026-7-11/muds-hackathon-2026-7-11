import Link from "next/link";
import { redirect } from "next/navigation";
import { auth } from "@/auth";
import { ProfileCard, type ResearchTag } from "@/components/profile-card";
import { serverApiFetch } from "@/lib/api-server";
import { getSessionRole } from "@/lib/session-role";
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
// 今回の募集期間の提出状況(準備中/未提出/提出済み)だけに応じて出し分ける。
// 過去の募集期間の提出状況は今回とは無関係なので表示しない。
function applicationStatusView(application: MyApplication | null): {
  label: string;
  buttonLabel: string | null;
} {
  if (application === null) {
    return { label: "取得できませんでした", buttonLabel: null };
  }
  if (!application.is_editable) {
    // 今回募集中の期間が無い(準備中/締切後)。過去の提出有無は問わない。
    return { label: "準備中", buttonLabel: null };
  }
  if (application.status === "submitted") {
    return { label: "提出済み", buttonLabel: "内容を編集" };
  }
  return { label: "未提出", buttonLabel: "志望を提出" };
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
  // マイページは学生向け(プロフィール・所属ゼミ・志望提出状況)の内容しか無く、
  // /applications/me もteacherには403を返す。ログイン直後は常にここへ
  // 着地する(login-button.tsxのsignIn()にcallbackUrl指定が無いため)が、
  // teacherのナビ(menu-bar.tsxのteacherNavItems)には「マイページ」自体が
  // 無く二度と辿り着けないので、教員だけログイン直後に自分のホームへ流す。
  const role = await getSessionRole();
  if (role === "teacher") {
    redirect("/assignment");
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
        <h1 className="border-l-4 border-[#add8e6] pl-3 text-2xl font-bold text-zinc-800">
          マイページ
        </h1>
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
              <section className="rounded-2xl border border-line bg-white p-6 text-zinc-500 shadow-sm shadow-[#add8e6]/30">
                プロフィールを取得できませんでした。
              </section>
            )}
          </div>

          <div className="flex flex-col gap-6 sm:w-72">
            <section className="rounded-2xl border border-line bg-white p-6 shadow-sm shadow-[#add8e6]/30">
              <p className="text-xs font-semibold uppercase tracking-wider text-zinc-400">
                Current Assignment
              </p>
              <p className="mt-2 text-lg font-semibold text-zinc-800">
                {me?.current_seminar?.name ?? "未配属"}
              </p>
            </section>

            <section className="rounded-2xl border border-line bg-white p-6 shadow-sm shadow-[#add8e6]/30">
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
