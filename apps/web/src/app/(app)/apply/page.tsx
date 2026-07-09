import { redirect } from "next/navigation";
import { auth } from "@/auth";
import {
  ApplicationForm,
  type ApplicationFormData,
  type Seminar,
} from "@/components/application-form";
import { serverApiFetch } from "@/lib/api-server";
import type { Session } from "next-auth";

async function getSeminars(session: Session | null): Promise<Seminar[]> {
  try {
    const res = await serverApiFetch("/seminars", session, {
      cache: "no-store",
    });
    if (!res.ok) {
      return [];
    }
    return (await res.json()) as Seminar[];
  } catch {
    return [];
  }
}

async function getApplication(
  session: Session | null,
): Promise<ApplicationFormData | null> {
  try {
    const res = await serverApiFetch("/applications/me", session, {
      cache: "no-store",
    });
    if (!res.ok) {
      return null;
    }
    return (await res.json()) as ApplicationFormData;
  } catch {
    return null;
  }
}

export default async function ApplyPage() {
  const session = await auth();
  if (!session) {
    redirect("/login");
  }

  const [seminars, application] = await Promise.all([
    getSeminars(session),
    getApplication(session),
  ]);

  return (
    <main className="relative flex flex-1 flex-col bg-[#e6e6e6]">
      <div className="relative mx-auto flex w-full max-w-3xl flex-1 flex-col gap-6 p-4 sm:p-6">
        <h1 className="border-l-4 border-[#add8e6] pl-3 text-2xl font-bold text-zinc-800">
          志望理由提出
        </h1>
        {application ? (
          <ApplicationForm
            seminars={seminars}
            initialApplication={application}
          />
        ) : (
          <section className="rounded-2xl border-2 border-[#add8e6] bg-white p-6 text-zinc-500 shadow-sm shadow-[#add8e6]/30">
            志望情報を取得できませんでした。時間をおいて再度お試しください。
          </section>
        )}
      </div>
    </main>
  );
}
