"use client";

import Link from "next/link";
import { useRef, useState } from "react";
import { useSession } from "next-auth/react";
import { apiFetch } from "@/lib/api-client";
import { SkySelect } from "@/components/sky-select";

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
  // 結果がどの募集ラウンドに対するものかを表示するため、
  // アップロード時点で選択されていたラウンドを結果と一緒に保持する
  // (selectedTermIdはこの後も変更されうるため、結果表示には使えない)。
  const [resultTerm, setResultTerm] = useState<AdminTermOption | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [isDraggingOver, setIsDraggingOver] = useState(false);

  function chooseFile(file: File | null): void {
    setErrorMessage(null);
    if (file && !file.name.toLowerCase().endsWith(".csv")) {
      setErrorMessage("CSVファイル(.csv)を選択してください。");
      return;
    }
    setSelectedFile(file);
  }

  function handleFileSelected(e: React.ChangeEvent<HTMLInputElement>): void {
    chooseFile(e.target.files?.[0] ?? null);
  }

  function handleDragOver(e: React.DragEvent<HTMLButtonElement>): void {
    e.preventDefault();
    if (!isUploading) {
      setIsDraggingOver(true);
    }
  }

  function handleDragLeave(e: React.DragEvent<HTMLButtonElement>): void {
    e.preventDefault();
    setIsDraggingOver(false);
  }

  function handleDrop(e: React.DragEvent<HTMLButtonElement>): void {
    e.preventDefault();
    setIsDraggingOver(false);
    if (isUploading) {
      return;
    }
    chooseFile(e.dataTransfer.files?.[0] ?? null);
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
    const uploadTerm = terms.find((term) => term.id === selectedTermId) ?? null;
    setIsUploading(true);
    setResult(null);
    setResultTerm(null);
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
      setResultTerm(uploadTerm);
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

  const termOptions = terms.map((term) => ({
    value: term.id,
    label: termLabel(term),
  }));

  return (
    <div className="flex flex-col gap-4">
      <section className="rounded-2xl border border-line bg-white p-4 shadow-sm">
        <h2 className="font-semibold text-zinc-800">配属結果CSVアップロード</h2>
        <p className="mt-1 text-sm text-zinc-500">
          列: student_id, seminar_id。どちらもIDと人が読める文字列の両方に
          対応しています(student_id: 学籍番号の生数字でも可、seminar_id:
          <Link
            href="/admin/seminars"
            className="text-zinc-500 underline underline-offset-2 hover:opacity-70"
          >
            ゼミ管理
          </Link>
          のIDまたはゼミ名)。該当する行が見つからない場合、結果にどちらが
          違うか(学生/ゼミ)を表示します。募集ラウンドはアップロード時に下で
          選択します(CSVには含めません)。既に存在する組み合わせはスキップ
          されます(再アップロードしても重複しません)。
        </p>

        {terms.length === 0 ? (
          <p className="mt-3 text-sm text-zinc-500">
            募集ラウンドがまだありません。先に
            <Link
              href="/admin/recruitment-terms"
              className="text-zinc-500 underline underline-offset-2 hover:opacity-70"
            >
              募集ラウンド管理
            </Link>
            で作成してください。
          </p>
        ) : (
          <div className="mt-3 flex flex-col gap-3">
            <div className="flex flex-col gap-1 text-sm text-zinc-600">
              <span>募集ラウンド</span>
              <SkySelect
                value={selectedTermId}
                options={termOptions}
                onChange={setSelectedTermId}
                ariaLabel="募集ラウンド"
              />
            </div>

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
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              disabled={isUploading}
              className={`flex w-full flex-col items-center gap-2 rounded-lg border-2 border-dashed p-6 text-center transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${
                isDraggingOver
                  ? "border-[#add8e6] bg-[#add8e6]/10"
                  : "border-line hover:border-[#add8e6] hover:bg-[#add8e6]/[.06]"
              }`}
            >
              <span className="text-sm text-zinc-700">
                CSVファイルをここにドラッグ&ドロップ、またはクリックして選択
              </span>
              <span className="text-sm text-zinc-500">
                {selectedFile ? selectedFile.name : "未選択"}
              </span>
            </button>
            <div className="flex flex-wrap items-center gap-2">
              <button
                type="button"
                onClick={handleUpload}
                disabled={isUploading}
                className="rounded-full bg-[#add8e6] px-4 py-2 text-sm font-semibold text-sky-950 shadow-sm transition-all hover:bg-[#9bcfe0] hover:shadow active:translate-y-px disabled:cursor-not-allowed disabled:opacity-50 focus:outline-none focus-visible:ring-4 focus-visible:ring-[#add8e6]/50"
              >
                {isUploading ? "アップロード中..." : "アップロードする"}
              </button>
            </div>
          </div>
        )}
      </section>

      {errorMessage && (
        <p className="rounded-2xl border-2 border-red-300 bg-white p-4 text-sm text-red-600 shadow-sm">
          {errorMessage}
        </p>
      )}

      {result && (
        <section className="rounded-2xl border border-line bg-white p-4 shadow-sm">
          <h2 className="font-semibold text-zinc-800">結果</h2>
          {resultTerm && (
            <p className="mt-1 text-sm text-zinc-500">
              対象ラウンド: {termLabel(resultTerm)}
            </p>
          )}
          <dl className="mt-2 flex flex-col gap-1 text-sm">
            <div className="flex gap-2">
              <dt className="text-zinc-500">作成件数</dt>
              <dd className="text-zinc-800">{result.created}</dd>
            </div>
            <div className="flex gap-2">
              <dt className="text-zinc-500">既存件数(スキップ)</dt>
              <dd className="text-zinc-800">{result.existing}</dd>
            </div>
            <div className="flex gap-2">
              <dt className="text-zinc-500">エラー件数</dt>
              <dd className="text-zinc-800">{result.errors.length}</dd>
            </div>
          </dl>
          {result.errors.length > 0 && (
            <ul className="mt-3 flex flex-col gap-1 text-sm">
              {result.errors.map((error) => (
                <li
                  key={error.row}
                  className="rounded-lg border border-line bg-[#add8e6]/[.06] px-3 py-1.5 text-zinc-700"
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
