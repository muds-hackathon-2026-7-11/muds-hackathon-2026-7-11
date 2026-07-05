"use client";

import { signIn } from "next-auth/react";

export default function LoginPage() {
  return (
    <main className="flex flex-1 items-center justify-center px-4">
      <button
        type="button"
        onClick={() => signIn("google")}
        className="rounded-md bg-black px-4 py-2 text-sm font-medium text-white hover:bg-zinc-800 dark:bg-white dark:text-black dark:hover:bg-zinc-200"
      >
        Googleでログイン
      </button>
    </main>
  );
}
