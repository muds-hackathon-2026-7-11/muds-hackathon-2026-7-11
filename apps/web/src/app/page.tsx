import { AuthStatus } from "@/components/auth-status";

export default function Home() {
  return (
    <div className="flex flex-1 items-center justify-center bg-zinc-50 font-sans dark:bg-black">
      <main className="flex w-full max-w-md flex-col gap-8 px-8">
        <div className="flex flex-col gap-2">
          <h1 className="text-2xl font-semibold tracking-tight text-black dark:text-zinc-50">
            🎓 ゼミナビ
          </h1>
          <p className="text-sm text-zinc-600 dark:text-zinc-400">
            ゼミ選択・配属支援プラットフォーム
          </p>
        </div>
        <AuthStatus />
      </main>
    </div>
  );
}
