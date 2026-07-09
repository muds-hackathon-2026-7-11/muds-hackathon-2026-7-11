"use client";

import { signIn } from "next-auth/react";
import Image from "next/image";
import logo from "@/app/logo.png";

export function LoginButton() {
  return (
    <section className="flex w-full max-w-lg flex-col items-center gap-6 rounded-2xl border border-[#e6e6e6] bg-white p-12 shadow-sm">
      <div className="flex flex-col items-center gap-3 text-center">
        <Image
          src={logo}
          alt="ロゴ"
          width={882}
          height={369}
          priority
          className="h-16 w-auto sm:h-20"
        />
        <p className="text-base text-zinc-500">ゼミ選択・配属支援システム</p>
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
