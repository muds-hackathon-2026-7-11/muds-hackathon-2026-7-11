"use client";

import { useRef, useState } from "react";
import { useSession } from "next-auth/react";
import { apiFetch } from "@/lib/api-client";

export type AssignmentImportError = {
  row: number;
  reason: string;
};

export type AssignmentImportResult = {
  created: number;
  existing: number;
  errors: AssignmentImportError[];
};

async function extractErrorDetail(res: Response): Promise<string> {
  try {
    const body = (await res.json()) as { detail?: string };
    return body.detail ?? "エラーが発生しました。";
  } catch {
    return "エラーが発生しました。";
  }
}

export function AdminAssignmentImportView() {
  const { data: session } = useSession();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [result, setResult] = useState<AssignmentImportResult | null>(null);
  const [isUploading, setIsUploading] = useState(false);

  async function handleFileSelected(
    e: React.ChangeEvent<HTMLInputElement>,
  ): Promise<void> {
    const file = e.target.files?.[0];
    if (!file) {
      return;
    }
    setErrorMessage(null);
    setResult(null);
    setIsUploading(true);
    try {
      const formData = new FormData();
      formData.append("file", file);
      // multipart/form-dataのboundaryはfetchが自動付与するため、
      // Content-Typeは明示的に指定しない。
      const res = await apiFetch("/admin/assignments/import", session, {
        method: "POST",
        body: formData,
      });
      if (!res.ok) {
        setErrorMessage(await extractErrorDetail(res));
        return;
      }
      const body = (await res.json()) as AssignmentImportResult;
      setResult(body);
    } catch {
      setErrorMessage("通信に失敗しました。時間をおいて再度お試しください。");
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <section className="rounded-lg border border-black/[.08] p-4 dark:border-white/[.145]">
        <h2 className="font-semibold">配属結果CSVアップロード</h2>
        <p className="mt-1 text-sm text-foreground/60">
          列: student_id(学籍番号), seminar_id, term_id(募集ラウンドのUUID)。
          既に存在する組み合わせはスキップされます(再アップロードしても重複しません)。
        </p>
        <input
          ref={fileInputRef}
          type="file"
          accept=".csv,text/csv"
          onChange={handleFileSelected}
          disabled={isUploading}
          className="hidden"
        />
        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          disabled={isUploading}
          className="mt-3 rounded-full bg-foreground px-4 py-2 text-sm font-medium text-background hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {isUploading
            ? "アップロード中..."
            : "CSVファイルを選択してアップロード"}
        </button>
      </section>

      {errorMessage && (
        <p className="rounded-lg border border-black/[.08] p-4 text-sm dark:border-white/[.145]">
          {errorMessage}
        </p>
      )}

      {result && (
        <section className="rounded-lg border border-black/[.08] p-4 dark:border-white/[.145]">
          <h2 className="font-semibold">結果</h2>
          <dl className="mt-2 flex flex-col gap-1 text-sm">
            <div className="flex gap-2">
              <dt className="text-foreground/60">作成件数</dt>
              <dd>{result.created}</dd>
            </div>
            <div className="flex gap-2">
              <dt className="text-foreground/60">既存件数(スキップ)</dt>
              <dd>{result.existing}</dd>
            </div>
            <div className="flex gap-2">
              <dt className="text-foreground/60">エラー件数</dt>
              <dd>{result.errors.length}</dd>
            </div>
          </dl>
          {result.errors.length > 0 && (
            <ul className="mt-3 flex flex-col gap-1 text-sm">
              {result.errors.map((error) => (
                <li
                  key={error.row}
                  className="rounded-lg border border-black/[.08] px-3 py-1.5 dark:border-white/[.145]"
                >
                  {error.row}行目: {error.reason}
                </li>
              ))}
            </ul>
          )}
        </section>
      )}
    </div>
  );
}
