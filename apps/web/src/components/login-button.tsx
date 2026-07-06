"use client";

import { signIn } from "next-auth/react";

export function LoginButton() {
  return (
    <button
      type="button"
      onClick={() => signIn("google")}
      className="rounded-md bg-black px-4 py-2 text-sm font-medium text-white hover:bg-zinc-800 dark:bg-white dark:text-black dark:hover:bg-zinc-200"
    >
      Googleでログイン
    </button>
  );
}
