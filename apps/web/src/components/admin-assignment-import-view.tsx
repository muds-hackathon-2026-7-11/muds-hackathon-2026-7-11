"use client";

import Link from "next/link";
import { useRef, useState } from "react";
import { useSession } from "next-auth/react";
import { apiFetch } from "@/lib/api-client";

export type AdminTermOption = {
  id: string;
  academic_year: number;
  starts_at: string;
  ends_at: string;
};

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

function formatDate(value: string): string {
  const d = new Date(value);
  return Number.isNaN(d.getTime())
    ? value
    : d.toLocaleDateString("ja-JP", {
        dateStyle: "medium",
        timeZone: "Asia/Tokyo",
      });
}

function termLabel(term: AdminTermOption): string {
  return `${term.academic_year}年度 (${formatDate(term.starts_at)} 〜 ${formatDate(term.ends_at)})`;
}

type AdminAssignmentImportViewProps = {
  terms: AdminTermOption[];
};

export function AdminAssignmentImportView({
  terms,
}: AdminAssignmentImportViewProps) {
  const { data: session } = useSession();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [selectedTermId, setSelectedTermId] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [result, setResult] = useState<AssignmentImportResult | null>(null);
  const [isUploading, setIsUploading] = useState(false);

  function handleFileSelected(e: React.ChangeEvent<HTMLInputElement>): void {
    setErrorMessage(null);
    setSelectedFile(e.target.files?.[0] ?? null);
  }

  async function handleUpload(): Promise<void> {
    setErrorMessage(null);
    if (!selectedTermId) {
      setErrorMessage("募集ラウンドを選択してください。");
      return;
    }
    if (!selectedFile) {
      setErrorMessage("CSVファイルを選択してください。");
      return;
    }
    setIsUploading(true);
    setResult(null);
    try {
      const formData = new FormData();
      formData.append("term_id", selectedTermId);
      formData.append("file", selectedFile);
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
      setSelectedFile(null);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    } catch {
      setErrorMessage("通信に失敗しました。時間をおいて再度お試しください。");
    } finally {
      setIsUploading(false);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <section className="rounded-lg border border-black/[.08] p-4 dark:border-white/[.145]">
        <h2 className="font-semibold">配属結果CSVアップロード</h2>
        <p className="mt-1 text-sm text-foreground/60">
          列: student_id, seminar_id。どちらもIDと人が読める文字列の両方に
          対応しています(student_id: 学籍番号の生数字でも可、seminar_id:
          <Link href="/admin/seminars" className="underline hover:opacity-70">
            ゼミ管理
          </Link>
          のIDまたはゼミ名)。該当する行が見つからない場合、結果にどちらが
          違うか(学生/ゼミ)を表示します。募集ラウンドはアップロード時に下で
          選択します(CSVには含めません)。既に存在する組み合わせはスキップ
          されます(再アップロードしても重複しません)。
        </p>

        {terms.length === 0 ? (
          <p className="mt-3 text-sm text-foreground/60">
            募集ラウンドがまだありません。先に
            <Link
              href="/admin/recruitment-terms"
              className="underline hover:opacity-70"
            >
              募集ラウンド管理
            </Link>
            で作成してください。
          </p>
        ) : (
          <div className="mt-3 flex flex-col gap-3">
            <label className="flex flex-col gap-1 text-sm">
              募集ラウンド
              <select
                value={selectedTermId}
                onChange={(e) => setSelectedTermId(e.target.value)}
                className="rounded-lg border border-black/[.08] bg-background px-3 py-2 text-sm dark:border-white/[.145]"
              >
                <option value="">選択してください</option>
                {terms.map((term) => (
                  <option key={term.id} value={term.id}>
                    {termLabel(term)}
                  </option>
                ))}
              </select>
            </label>

            <div className="flex flex-wrap items-center gap-2">
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
                className="rounded-full border border-black/[.08] px-4 py-2 text-sm font-medium hover:bg-black/[.04] disabled:cursor-not-allowed disabled:opacity-50 dark:border-white/[.145] dark:hover:bg-white/[.08]"
              >
                CSVファイルを選択
              </button>
              <span className="text-sm text-foreground/60">
                {selectedFile ? selectedFile.name : "未選択"}
              </span>
              <button
                type="button"
                onClick={handleUpload}
                disabled={isUploading}
                className="rounded-full bg-foreground px-4 py-2 text-sm font-medium text-background hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {isUploading ? "アップロード中..." : "アップロードする"}
              </button>
            </div>
          </div>
        )}
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
