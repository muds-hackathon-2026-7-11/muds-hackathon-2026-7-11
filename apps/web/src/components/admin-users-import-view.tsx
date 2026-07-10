"use client";

import { useSession } from "next-auth/react";
import { useRef, useState } from "react";
import { apiFetch } from "@/lib/api-client";

export type UserImportSkip = {
  row: number;
  email: string;
  reason: string;
};

export type UserImportResult = {
  created: number;
  updated: number;
  deactivated: number;
  skipped: UserImportSkip[];
};

async function extractErrorDetail(res: Response): Promise<string> {
  try {
    const body = (await res.json()) as { detail?: string };
    return body.detail ?? "エラーが発生しました。";
  } catch {
    return "エラーが発生しました。";
  }
}

export function AdminUsersImportView() {
  const { data: session } = useSession();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [result, setResult] = useState<UserImportResult | null>(null);
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
    if (!selectedFile) {
      setErrorMessage("CSVファイルを選択してください。");
      return;
    }
    setIsUploading(true);
    setResult(null);
    try {
      const formData = new FormData();
      formData.append("file", selectedFile);
      // multipart/form-dataのboundaryはfetchが自動付与するため、
      // Content-Typeは明示的に指定しない。
      const res = await apiFetch("/admin/users/import", session, {
        method: "POST",
        body: formData,
      });
      if (!res.ok) {
        setErrorMessage(await extractErrorDetail(res));
        return;
      }
      const body = (await res.json()) as UserImportResult;
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
      <section className="rounded-2xl border-2 border-[#add8e6] bg-white p-4 shadow-sm">
        <h2 className="font-semibold text-zinc-800">
          学生・教員名簿CSVアップロード
        </h2>
        <p className="mt-1 text-sm text-zinc-500">
          Slack管理画面からエクスポートした、ワークスペースメンバー一覧CSVを
          そのままアップロードしてください(列: username, email, status,
          billing-active, has-2fa, has-sso, userid, fullname, displayname,
          expiration-timestamp。<code>make import-users</code>
          と同じ形式です)。学年更新・新入生の追加を行い、CSVに存在しなく
          なった学生(卒業・退学)は非アクティブ化されます。教員は
          非アクティブ化の対象外です。
        </p>

        <div className="mt-3 flex flex-col gap-3">
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
                : "border-[#add8e6]/60 hover:border-[#add8e6] hover:bg-[#add8e6]/[.06]"
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
      </section>

      {errorMessage && (
        <p className="rounded-2xl border-2 border-red-300 bg-white p-4 text-sm text-red-600 shadow-sm">
          {errorMessage}
        </p>
      )}

      {result && (
        <section className="rounded-2xl border-2 border-[#add8e6] bg-white p-4 shadow-sm">
          <h2 className="font-semibold text-zinc-800">結果</h2>
          <dl className="mt-2 flex flex-col gap-1 text-sm">
            <div className="flex gap-2">
              <dt className="text-zinc-500">新規作成</dt>
              <dd className="text-zinc-800">{result.created}</dd>
            </div>
            <div className="flex gap-2">
              <dt className="text-zinc-500">更新</dt>
              <dd className="text-zinc-800">{result.updated}</dd>
            </div>
            <div className="flex gap-2">
              <dt className="text-zinc-500">非アクティブ化(卒業・退学)</dt>
              <dd className="text-zinc-800">{result.deactivated}</dd>
            </div>
            <div className="flex gap-2">
              <dt className="text-zinc-500">スキップ件数</dt>
              <dd className="text-zinc-800">{result.skipped.length}</dd>
            </div>
          </dl>
          {result.skipped.length > 0 && (
            <ul className="mt-3 flex flex-col gap-1 text-sm">
              {result.skipped.map((skip) => (
                <li
                  key={skip.row}
                  className="rounded-lg border border-[#add8e6]/60 bg-[#add8e6]/[.06] px-3 py-1.5 text-zinc-700"
                >
                  {skip.row}行目({skip.email}): {skip.reason}
                </li>
              ))}
            </ul>
          )}
        </section>
      )}
    </div>
  );
}
