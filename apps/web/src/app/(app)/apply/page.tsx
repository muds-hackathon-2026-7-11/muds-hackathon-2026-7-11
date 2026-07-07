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
    <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-4 p-4">
      <h1 className="text-xl font-semibold">志望提出</h1>

      {application ? (
        <ApplicationForm seminars={seminars} initialApplication={application} />
      ) : (
        <section className="rounded-lg border border-black/[.08] p-6 text-foreground/60 dark:border-white/[.145]">
          志望情報を取得できませんでした。時間をおいて再度お試しください。
        </section>
      )}
    </main>
  );
}
