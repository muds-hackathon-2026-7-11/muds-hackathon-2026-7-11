"use client";

import { signIn, signOut, useSession } from "next-auth/react";

export function AuthStatus() {
  const { data: session, status } = useSession();

  if (status === "loading") {
    return <p className="text-zinc-500">読み込み中...</p>;
  }

  if (!session) {
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

  return (
    <div className="flex flex-col items-start gap-3">
      <div className="text-sm text-zinc-700 dark:text-zinc-300">
        <p>
          ログイン中: <span className="font-medium">{session.user?.name}</span>
        </p>
        <p className="text-zinc-500">{session.user?.email}</p>
      </div>
      <button
        type="button"
        onClick={() => signOut()}
        className="rounded-md border border-zinc-300 px-4 py-2 text-sm font-medium hover:bg-zinc-100 dark:border-zinc-700 dark:hover:bg-zinc-900"
      >
        ログアウト
      </button>
    </div>
  );
}
