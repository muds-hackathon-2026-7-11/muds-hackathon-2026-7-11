import Link from "next/link";

export default function AdminIndexPage() {
  return (
    <main className="relative flex flex-1 flex-col bg-[#e6e6e6]">
      <div className="relative mx-auto flex w-full max-w-3xl flex-1 flex-col gap-6 p-4 sm:p-6">
        <h1 className="text-2xl font-bold text-zinc-900">管理者メニュー</h1>

        <div className="flex flex-col gap-3">
          <Link
            href="/admin/seminars"
            className="rounded-2xl border-2 border-[#add8e6] bg-white p-4 text-sm font-medium text-zinc-900 shadow-sm shadow-[#add8e6]/30 transition-colors hover:bg-[#add8e6]/10"
          >
            ゼミ管理
          </Link>
          <Link
            href="/admin/teachers"
            className="rounded-2xl border-2 border-[#add8e6] bg-white p-4 text-sm font-medium text-zinc-900 shadow-sm shadow-[#add8e6]/30 transition-colors hover:bg-[#add8e6]/10"
          >
            教員・管理者管理
          </Link>
          <Link
            href="/admin/recruitment-terms"
            className="rounded-2xl border-2 border-[#add8e6] bg-white p-4 text-sm font-medium text-zinc-900 shadow-sm shadow-[#add8e6]/30 transition-colors hover:bg-[#add8e6]/10"
          >
            募集ラウンド管理
          </Link>
          <Link
            href="/admin/assignments"
            className="rounded-2xl border-2 border-[#add8e6] bg-white p-4 text-sm font-medium text-zinc-900 shadow-sm shadow-[#add8e6]/30 transition-colors hover:bg-[#add8e6]/10"
          >
            配属結果インポート
          </Link>
        </div>
      </div>
    </main>
  );
}
