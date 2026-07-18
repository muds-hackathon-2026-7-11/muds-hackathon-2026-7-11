"use client";

import { useMemo, useState } from "react";

export type UnsubmittedApplicant = {
  student_id: string | null;
  name: string;
  grade: string | null;
};

const GRADE_FILTERS = ["すべて", "B1", "B2", "B3", "B4"] as const;

type TeacherUnsubmittedViewProps = {
  applicants: UnsubmittedApplicant[];
};

export function TeacherUnsubmittedView({
  applicants,
}: TeacherUnsubmittedViewProps) {
  const [gradeFilter, setGradeFilter] =
    useState<(typeof GRADE_FILTERS)[number]>("すべて");

  const filtered = useMemo(
    () =>
      gradeFilter === "すべて"
        ? applicants
        : applicants.filter((applicant) => applicant.grade === gradeFilter),
    [applicants, gradeFilter],
  );

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex flex-wrap gap-1">
          {GRADE_FILTERS.map((grade) => (
            <button
              key={grade}
              type="button"
              onClick={() => setGradeFilter(grade)}
              aria-pressed={gradeFilter === grade}
              className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
                gradeFilter === grade
                  ? "bg-[#add8e6] text-sky-950"
                  : "border border-[#add8e6]/60 text-zinc-600 hover:bg-[#add8e6]/10"
              }`}
            >
              {grade}
            </button>
          ))}
        </div>
        <span className="text-sm text-zinc-500">
          {filtered.length}名 / 全{applicants.length}名 未提出
        </span>
      </div>

      {filtered.length === 0 ? (
        <p className="text-sm text-zinc-500">未提出の学生はいません。</p>
      ) : (
        <div className="overflow-x-auto rounded-2xl border-2 border-[#add8e6] bg-white shadow-sm shadow-[#add8e6]/30">
          <table className="w-full min-w-[420px] text-sm">
            <thead>
              <tr className="border-b border-[#add8e6]/40 text-left text-xs font-semibold text-zinc-500">
                <th className="px-4 py-2">氏名</th>
                <th className="px-4 py-2">学年</th>
                <th className="px-4 py-2">学籍番号</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((applicant, index) => (
                <tr
                  key={`${applicant.student_id ?? applicant.name}-${index}`}
                  className="border-b border-[#add8e6]/20 last:border-0"
                >
                  <td className="px-4 py-2 font-medium text-zinc-800">
                    {applicant.name}
                  </td>
                  <td className="px-4 py-2 text-zinc-600">
                    {applicant.grade ?? "学年不明"}
                  </td>
                  <td className="px-4 py-2 text-zinc-600">
                    {applicant.student_id ?? "-"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
