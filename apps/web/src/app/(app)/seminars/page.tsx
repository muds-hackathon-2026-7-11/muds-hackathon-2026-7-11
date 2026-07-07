import Link from "next/link";
import { redirect } from "next/navigation";
import { auth } from "@/auth";
import { serverApiFetch } from "@/lib/api-server";
import type { Session } from "next-auth";

type Seminar = {
  id: string;
  name: string;
  description: string | null;
  photo_url: string | null;
  capacity: number | null;
};

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

export default async function SeminarsPage() {
  const session = await auth();
  if (!session) {
    redirect("/login");
  }

  const seminars = await getSeminars(session);

  return (
    <main className="mx-auto flex w-full max-w-5xl flex-1 flex-col gap-4 p-4">
      <h1 className="text-xl font-semibold">ゼミ一覧</h1>

      {seminars.length === 0 ? (
        <p className="text-foreground/60">ゼミ情報を取得できませんでした。</p>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {seminars.map((seminar) => (
            <Link
              key={seminar.id}
              href={`/seminars/${seminar.id}`}
              className="flex flex-col gap-2 rounded-lg border border-black/[.08] p-4 hover:bg-black/[.02] dark:border-white/[.145] dark:hover:bg-white/[.03]"
            >
              {seminar.photo_url && (
                // biome-ignore lint/performance/noImgElement: photo_urlは任意の外部ドメインのため next/image のドメイン許可設定が不要なimgタグを使う
                <img
                  src={seminar.photo_url}
                  alt={seminar.name}
                  className="h-32 w-full rounded-md object-cover"
                />
              )}
              <p className="font-semibold">{seminar.name}</p>
              <p className="line-clamp-2 text-sm text-foreground/60">
                {seminar.description ?? "研究内容は未設定です。"}
              </p>
              <p className="text-xs text-foreground/60">
                定員: {seminar.capacity ?? "未設定"}
              </p>
            </Link>
          ))}
        </div>
      )}
    </main>
  );
}
