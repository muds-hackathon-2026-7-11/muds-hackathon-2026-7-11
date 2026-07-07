import Link from "next/link";

export default function AdminIndexPage() {
  return (
    <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-4 p-4">
      <h1 className="text-xl font-semibold">管理者メニュー</h1>

      <div className="flex flex-col gap-3">
        <Link
          href="/admin/seminars"
          className="rounded-lg border border-black/[.08] p-4 text-sm font-medium hover:bg-black/[.04] dark:border-white/[.145] dark:hover:bg-white/[.08]"
        >
          ゼミ管理
        </Link>
        <Link
          href="/admin/teachers"
          className="rounded-lg border border-black/[.08] p-4 text-sm font-medium hover:bg-black/[.04] dark:border-white/[.145] dark:hover:bg-white/[.08]"
        >
          教員管理
        </Link>
      </div>
    </main>
  );
}
