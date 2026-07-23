"use client";

import { useSession } from "next-auth/react";
import { useState } from "react";
import { apiFetch } from "@/lib/api-client";

export type PastSeminar = {
  seminar_name: string;
  academic_year: number;
};

export type Applicant = {
  student_id: string | null;
  name: string;
  grade: string | null;
  priority: number;
  reason: string;
  past_seminars: PastSeminar[];
};

export type SeminarApplicants = {
  seminar_id: string;
  seminar_name: string;
  applicants: Applicant[];
};

const PRIORITY_LABEL: Record<number, string> = {
  1: "第1志望",
  2: "第2志望",
  3: "第3志望",
};

async function extractErrorDetail(res: Response): Promise<string> {
  try {
    const body = (await res.json()) as { detail?: string };
    return body.detail ?? "エラーが発生しました。";
  } catch {
    return "エラーが発生しました。";
  }
}

type TeacherApplicantsViewProps = {
  initialData: SeminarApplicants[];
};

export function TeacherApplicantsView({
  initialData,
}: TeacherApplicantsViewProps) {
  const { data: session } = useSession();
  const [expandedKey, setExpandedKey] = useState<string | null>(null);
  const [downloadingTarget, setDownloadingTarget] = useState<
    "mine" | "all" | null
  >(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  function toggleExpanded(key: string): void {
    setExpandedKey((prev) => (prev === key ? null : key));
  }

  async function handleDownloadCsv(
    target: "mine" | "all",
    path: string,
    filename: string,
  ): Promise<void> {
    setErrorMessage(null);
    setDownloadingTarget(target);
    try {
      const res = await apiFetch(path, session);
      if (!res.ok) {
        setErrorMessage(await extractErrorDetail(res));
        return;
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    } catch {
      setErrorMessage("通信に失敗しました。時間をおいて再度お試しください。");
    } finally {
      setDownloadingTarget(null);
    }
  }

  const totalApplicants = initialData.reduce(
    (sum, seminar) => sum + seminar.applicants.length,
    0,
  );

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          onClick={() =>
            handleDownloadCsv(
              "mine",
              "/teacher/applicants.csv",
              "applicants.csv",
            )
          }
          disabled={downloadingTarget !== null || totalApplicants === 0}
          className="rounded-full bg-[#add8e6] px-5 py-2 text-sm font-semibold text-sky-950 shadow-sm transition-all hover:bg-[#9bcfe0] hover:shadow active:translate-y-px disabled:cursor-not-allowed disabled:opacity-50 focus:outline-none focus-visible:ring-4 focus-visible:ring-[#add8e6]/50"
        >
          {downloadingTarget === "mine"
            ? "ダウンロード中..."
            : "自分のゼミCSVダウンロード"}
        </button>
        <button
          type="button"
          onClick={() =>
            handleDownloadCsv(
              "all",
              "/teacher/applicants/all.csv",
              "applicants_all.csv",
            )
          }
          disabled={downloadingTarget !== null}
          className="rounded-full border border-[#add8e6]/60 px-5 py-2 text-sm font-medium text-zinc-700 transition-colors hover:bg-[#add8e6]/10 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {downloadingTarget === "all"
            ? "ダウンロード中..."
            : "全体CSVダウンロード"}
        </button>
      </div>

      {errorMessage && (
        <p className="rounded-2xl border-2 border-red-300 bg-white p-4 text-sm text-red-600 shadow-sm">
          {errorMessage}
        </p>
      )}

      {initialData.length === 0 ? (
        <p className="text-sm text-zinc-500">担当しているゼミがありません。</p>
      ) : (
        initialData.map((seminar) => (
          <section
            key={seminar.seminar_id}
            className="rounded-2xl border border-line bg-white p-6 shadow-sm shadow-[#add8e6]/30"
          >
            <h2 className="text-lg font-bold text-zinc-900">
              {seminar.seminar_name}
            </h2>

            {seminar.applicants.length === 0 ? (
              <p className="mt-3 text-sm text-zinc-500">
                まだ応募者がいません。
              </p>
            ) : (
              <div className="mt-3 flex flex-col gap-2">
                {seminar.applicants.map((applicant, index) => {
                  const key = `${seminar.seminar_id}-${index}`;
                  const isExpanded = expandedKey === key;
                  return (
                    <div
                      key={key}
                      className="rounded-lg border border-line"
                    >
                      <button
                        type="button"
                        onClick={() => toggleExpanded(key)}
                        aria-expanded={isExpanded}
                        className="flex w-full items-center justify-between gap-3 px-3 py-2 text-left hover:bg-[#add8e6]/10"
                      >
                        <div className="flex flex-wrap items-baseline gap-2">
                          <span className="rounded-full bg-[#add8e6]/30 px-2.5 py-0.5 text-xs font-semibold text-sky-950">
                            {PRIORITY_LABEL[applicant.priority] ??
                              `第${applicant.priority}志望`}
                          </span>
                          <span className="font-semibold text-zinc-800">
                            {applicant.name}
                          </span>
                          <span className="text-xs text-zinc-500">
                            {applicant.grade ?? "学年不明"}
                            {applicant.student_id
                              ? ` / ${applicant.student_id}`
                              : ""}
                          </span>
                        </div>
                        <span
                          aria-hidden
                          className="text-zinc-400 transition-transform"
                          style={{
                            transform: isExpanded
                              ? "rotate(180deg)"
                              : "rotate(0deg)",
                          }}
                        >
                          ▾
                        </span>
                      </button>

                      {isExpanded && (
                        <div className="border-t border-line px-3 py-3">
                          <p className="text-xs font-semibold text-zinc-500">
                            志望理由
                          </p>
                          <p className="mt-1 whitespace-pre-wrap text-sm text-zinc-700">
                            {applicant.reason}
                          </p>

                          <p className="mt-3 text-xs font-semibold text-zinc-500">
                            過去の所属ゼミ
                          </p>
                          {applicant.past_seminars.length === 0 ? (
                            <p className="mt-1 text-sm text-zinc-500">なし</p>
                          ) : (
                            <ul className="mt-1 flex flex-wrap gap-x-3 gap-y-1 text-sm text-zinc-700">
                              {applicant.past_seminars.map((past) => (
                                <li
                                  key={`${past.seminar_name}-${past.academic_year}`}
                                >
                                  {past.seminar_name}({past.academic_year})
                                </li>
                              ))}
                            </ul>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </section>
        ))
      )}
    </div>
  );
}
