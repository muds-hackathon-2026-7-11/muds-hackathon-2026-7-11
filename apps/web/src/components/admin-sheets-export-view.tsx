"use client";

import { useSession } from "next-auth/react";
import { useState } from "react";
import { apiFetch } from "@/lib/api-client";
import { extractErrorDetail } from "@/lib/extract-error-detail";

type AdminSheetsExportViewProps = {
  initialKey: string | null;
};

export function AdminSheetsExportView({
  initialKey,
}: AdminSheetsExportViewProps) {
  const { data: session } = useSession();
  const [exportKey, setExportKey] = useState(initialKey);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isRegenerating, setIsRegenerating] = useState(false);
  const [copied, setCopied] = useState(false);

  async function handleRegenerate(): Promise<void> {
    if (
      exportKey !== null &&
      !window.confirm(
        "再発行すると、今のキーを使っているApps Scriptは動かなくなります。よろしいですか?",
      )
    ) {
      return;
    }
    setErrorMessage(null);
    setCopied(false);
    setIsRegenerating(true);
    try {
      const res = await apiFetch(
        "/admin/sheets-export-key/regenerate",
        session,
        {
          method: "POST",
        },
      );
      if (!res.ok) {
        setErrorMessage(await extractErrorDetail(res));
        return;
      }
      const data = (await res.json()) as { key: string | null };
      setExportKey(data.key);
    } catch {
      setErrorMessage("通信に失敗しました。時間をおいて再度お試しください。");
    } finally {
      setIsRegenerating(false);
    }
  }

  async function handleCopy(): Promise<void> {
    if (!exportKey) {
      return;
    }
    await navigator.clipboard.writeText(exportKey);
    setCopied(true);
  }

  return (
    <section className="rounded-2xl border border-line bg-white p-6 shadow-sm shadow-[#add8e6]/30">
      <h2 className="text-lg font-bold text-zinc-900">
        スプレッドシート自動連携キー
      </h2>
      <p className="mt-2 text-sm text-zinc-500">
        志望理由データをGoogleスプレッドシートへ自動反映するApps
        Scriptを認証するための専用キー。設定手順はdocs/sheets-export.mdを参照。
      </p>

      {errorMessage && (
        <p className="mt-3 rounded-lg border border-line bg-white p-3 text-sm text-red-600">
          {errorMessage}
        </p>
      )}

      <div className="mt-4 flex flex-col gap-2">
        {exportKey ? (
          <div className="flex flex-wrap items-center gap-2">
            <code className="min-w-0 flex-1 truncate rounded-lg border border-line bg-white px-3 py-2 text-sm text-zinc-800">
              {exportKey}
            </code>
            <button
              type="button"
              onClick={handleCopy}
              className="shrink-0 rounded-full border border-[#add8e6]/60 px-4 py-2 text-sm font-medium text-zinc-700 transition-colors hover:bg-[#add8e6]/10"
            >
              {copied ? "コピーしました" : "コピー"}
            </button>
          </div>
        ) : (
          <p className="text-sm text-zinc-500">まだ発行されていません。</p>
        )}

        <button
          type="button"
          onClick={handleRegenerate}
          disabled={isRegenerating}
          className="self-start rounded-full bg-[#add8e6] px-5 py-2 text-sm font-semibold text-sky-950 shadow-sm transition-all hover:bg-[#9bcfe0] disabled:cursor-not-allowed disabled:opacity-50"
        >
          {isRegenerating ? "発行中..." : exportKey ? "再発行する" : "発行する"}
        </button>
      </div>
    </section>
  );
}
