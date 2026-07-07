"use client";

import { signIn } from "next-auth/react";

export function LoginButton() {
  return (
    <section className="flex w-full max-w-lg flex-col items-center gap-12 rounded-2xl border border-[#e6e6e6] bg-white p-12 shadow-sm">
      <div className="flex flex-col items-center gap-3 text-center">
        <h1 className="whitespace-nowrap text-6xl font-bold tracking-tight text-zinc-900 sm:text-7xl">
          Zemi-Match
        </h1>
        <p className="text-base text-zinc-500">
          ゼミ選択・配属支援プラットフォーム
        </p>
      </div>

      <button
        type="button"
        onClick={() => signIn("google")}
        className="rounded-lg bg-[#add8e6] px-8 py-4 text-base font-medium text-zinc-900 shadow-sm transition-all hover:translate-y-0.5 hover:bg-[#9ccbdd] active:translate-y-1 focus:outline-none focus-visible:ring-4 focus-visible:ring-[#add8e6]"
      >
        Googleでログイン
      </button>
    </section>
  );
}
