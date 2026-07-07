"use client";

import { signIn } from "next-auth/react";

export function LoginButton() {
  return (
    <section className="flex w-full max-w-sm flex-col items-center gap-10 rounded-lg border border-black/[.08] bg-background/80 p-6 backdrop-blur dark:border-white/[.145]">
      <div className="flex flex-col items-center gap-2 text-center">
        <h1 className="text-5xl font-bold tracking-tight text-zinc-900 drop-shadow-sm sm:text-6xl dark:text-zinc-50">
          Zemi-Match
        </h1>
        <p className="text-sm text-foreground/60">
          ゼミ選択・配属支援プラットフォーム
        </p>
      </div>

      <button
        type="button"
        onClick={() => signIn("google")}
        className="rounded-md bg-zinc-900 px-6 py-3 text-sm font-medium text-white shadow-lg shadow-zinc-900/30 transition-all hover:translate-y-0.5 hover:bg-zinc-700 hover:shadow-md hover:shadow-zinc-900/20 active:translate-y-1 active:shadow-sm focus:outline-none focus-visible:ring-4 focus-visible:ring-zinc-500 dark:bg-white dark:text-zinc-900 dark:shadow-white/20 dark:hover:bg-zinc-200"
      >
        Googleでログイン
      </button>
    </section>
  );
}
