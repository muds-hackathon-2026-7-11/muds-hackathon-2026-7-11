"use client";

import { useSession } from "next-auth/react";
import { useState } from "react";
import { apiFetch } from "@/lib/api-client";
import { SkyDatePicker } from "@/components/sky-date-picker";
import { SkySelect } from "@/components/sky-select";

export type AdminRecruitmentTerm = {
  id: string;
  academic_year: number;
  starts_at: string;
  ends_at: string;
  status: "preparing" | "open" | "closed";
  // ゼミ別設定を横断した対象学年の要約(#99)。対象学年はゼミごとの設定
  // (SeminarRecruitment)なので、募集ラウンド自体には値を持たない。
  // ラウンド作成直後に一括適用した値を、編集不要な確認用テキストとして
  // ラウンドのカード上に直接出す(「ゼミ別設定」を開かなくても確認できる
  // ように)。
  target_grades_summary: string;
};

export type AdminSeminarRecruitment = {
  seminar_id: string;
  seminar_name: string;
  capacity: number | null;
  target_grades: string[] | null;
};

export type AdminSeminarOption = {
  id: string;
  name: string;
};

// 対象学年(#99)。学部4年までしか使わないためB1〜B4のみ。空配列は
// 「募集していない」を意味する。
const GRADE_OPTIONS = ["B1", "B2", "B3", "B4"] as const;

// 新規ラウンド作成時に対象学年を全ゼミへ一括適用する際の仮の定員。
// 定員はゼミごとに差が大きいため、ここでは「0人のまま放置されて誰も
// 応募できなくなる」ことだけ避ける仮値とし、実際の値は「ゼミ別設定」で
// 個別に調整してもらう想定。
const BULK_DEFAULT_CAPACITY = 10;

const STATUS_LABEL: Record<AdminRecruitmentTerm["status"], string> = {
  preparing: "準備中",
  open: "募集中",
  closed: "終了",
};

// 状態セレクト(SkySelect)の選択肢。STATUS_LABELと同じ並び。
const STATUS_OPTIONS: {
  value: AdminRecruitmentTerm["status"];
  label: string;
}[] = [
  { value: "preparing", label: STATUS_LABEL.preparing },
  { value: "open", label: STATUS_LABEL.open },
  { value: "closed", label: STATUS_LABEL.closed },
];

// ゼミ別の対象学年を横断して、ラウンド単位の要約テキストにする。
// 全ゼミで同じ設定なら学年をそのまま表示し、ゼミごとに違えば「ゼミにより
// 異なる」とだけ表示する(個別の内訳は「ゼミ別設定」で確認する)。
export function summarizeTargetGrades(
  recruitments: AdminSeminarRecruitment[],
): string {
  const gradeSets = recruitments
    .map((r) => r.target_grades)
    .filter((g): g is string[] => g !== null);
  if (gradeSets.length === 0) {
    return "未設定";
  }
  const canonicalize = (grades: string[]) =>
    GRADE_OPTIONS.filter((g) => grades.includes(g)).join(",");
  const serialized = gradeSets.map(canonicalize);
  const allSame = serialized.every((s) => s === serialized[0]);
  if (!allSame) {
    return "ゼミにより異なる";
  }
  return serialized[0] === "" ? "対象学年なし" : serialized[0].split(",").join(", ");
}

// バックエンドのget_current_term(status=open かつ starts_at<=今日<=ends_at)
// と同じ条件。status=openのまま終了日を過ぎているだけの募集ラウンドは、
// 実質closedと同じ(志望提出を受け付けない)なので表示上も「終了」にする。
// (DB上のstatus自体はopenのままなので、編集フォームを開くと募集中の
// ままになっている点に注意)
function todayDateString(): string {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function isWithinPeriod(term: AdminRecruitmentTerm): boolean {
  const today = todayDateString();
  return term.starts_at <= today && today <= term.ends_at;
}

// 新規作成フォームを開いた日の年度(暦年)。年度欄の初期値に使う。
// new Date()はSSRとクライアントで値がずれ得るため、サーバー描画時ではなく
// フォームを開く(クライアント操作)タイミングで呼ぶ。
function currentAcademicYear(): string {
  return String(new Date().getFullYear());
}

function statusLabel(term: AdminRecruitmentTerm): string {
  if (term.status === "open" && !isWithinPeriod(term)) {
    return STATUS_LABEL.closed;
  }
  return STATUS_LABEL[term.status];
}

async function extractErrorDetail(res: Response): Promise<string> {
  try {
    const body = (await res.json()) as { detail?: string };
    return body.detail ?? "エラーが発生しました。";
  } catch {
    return "エラーが発生しました。";
  }
}

function formatPeriod(startsAt: string, endsAt: string): string {
  const format = (value: string) => {
    const d = new Date(value);
    return Number.isNaN(d.getTime())
      ? value
      : // サーバーとブラウザでデフォルトタイムゾーンが異なるとSSRと
        // ハイドレーション時で表示がずれるため、明示的に固定する。
        d.toLocaleDateString("ja-JP", {
          dateStyle: "medium",
          timeZone: "Asia/Tokyo",
        });
  };
  return `${format(startsAt)} 〜 ${format(endsAt)}`;
}

type RecruitmentInput = {
  capacity: string;
  targetGrades: string[];
};

function defaultRecruitmentInput(): RecruitmentInput {
  return { capacity: "", targetGrades: [...GRADE_OPTIONS] };
}

function buildRecruitmentInputs(
  recruitments: AdminSeminarRecruitment[],
): Record<string, RecruitmentInput> {
  const map: Record<string, RecruitmentInput> = {};
  for (const r of recruitments) {
    map[r.seminar_id] = {
      capacity: r.capacity === null ? "" : String(r.capacity),
      targetGrades: r.target_grades ?? [...GRADE_OPTIONS],
    };
  }
  return map;
}

type AdminRecruitmentTermsViewProps = {
  initialTerms: AdminRecruitmentTerm[];
  allSeminars: AdminSeminarOption[];
};

export function AdminRecruitmentTermsView({
  initialTerms,
  allSeminars,
}: AdminRecruitmentTermsViewProps) {
  const { data: session } = useSession();
  const [terms, setTerms] = useState(initialTerms);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const [isCreateFormOpen, setIsCreateFormOpen] = useState(false);
  const [newAcademicYear, setNewAcademicYear] = useState("");
  const [newStartsAt, setNewStartsAt] = useState("");
  const [newEndsAt, setNewEndsAt] = useState("");
  const [newStatus, setNewStatus] =
    useState<AdminRecruitmentTerm["status"]>("preparing");
  const [newBulkTargetGrades, setNewBulkTargetGrades] = useState<string[]>([
    ...GRADE_OPTIONS,
  ]);
  const [isCreating, setIsCreating] = useState(false);

  const [editingId, setEditingId] = useState<string | null>(null);
  const [editStartsAt, setEditStartsAt] = useState("");
  const [editEndsAt, setEditEndsAt] = useState("");
  const [editStatus, setEditStatus] =
    useState<AdminRecruitmentTerm["status"]>("preparing");
  const [isSavingEdit, setIsSavingEdit] = useState(false);

  const [selectedTermId, setSelectedTermId] = useState<string | null>(null);
  const [isLoadingRecruitments, setIsLoadingRecruitments] = useState(false);
  const [recruitments, setRecruitments] = useState<AdminSeminarRecruitment[]>(
    [],
  );
  const [recruitmentInputs, setRecruitmentInputs] = useState<
    Record<string, RecruitmentInput>
  >({});
  const [isSavingRecruitments, setIsSavingRecruitments] = useState(false);

  function openCreateForm(): void {
    setIsCreateFormOpen(true);
    // 年度は未入力ではなく、フォームを開いた日の年度を初期値にする。
    setNewAcademicYear(currentAcademicYear());
    setErrorMessage(null);
  }

  function resetCreateForm(): void {
    setIsCreateFormOpen(false);
    setNewAcademicYear("");
    setNewStartsAt("");
    setNewEndsAt("");
    setNewStatus("preparing");
    setNewBulkTargetGrades([...GRADE_OPTIONS]);
  }

  function cancelCreate(): void {
    resetCreateForm();
    setErrorMessage(null);
  }

  function toggleNewBulkTargetGrade(grade: string): void {
    setNewBulkTargetGrades((prev) => {
      const next = prev.includes(grade)
        ? prev.filter((g) => g !== grade)
        : [...prev, grade];
      return GRADE_OPTIONS.filter((g) => next.includes(g));
    });
  }

  // 新規ラウンド作成直後は全ゼミが未設定(定員null)のままで、そのままだと
  // 誰も応募できない状態が続いてしまう。対象学年を全ゼミへ一括適用して
  // その事故を防ぐ(定員は仮値。ゼミごとの調整は「ゼミ別設定」で行う)。
  async function applyBulkTargetGrades(
    termId: string,
    targetGrades: string[],
  ): Promise<void> {
    const results = await Promise.all(
      allSeminars.map((seminar) =>
        apiFetch(
          `/admin/recruitment-terms/${termId}/seminars/${seminar.id}`,
          session,
          {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              capacity: BULK_DEFAULT_CAPACITY,
              target_grades: targetGrades,
            }),
          },
        ),
      ),
    );
    const failedCount = results.filter((res) => !res.ok).length;
    if (failedCount > 0) {
      setErrorMessage(
        `募集ラウンドは作成しましたが、対象学年の一括設定に${failedCount}件失敗しました。「ゼミ別設定」から個別に確認してください。`,
      );
    }
  }

  async function handleCreate(): Promise<void> {
    setErrorMessage(null);
    const academicYear = Number(newAcademicYear);
    if (newAcademicYear.trim() === "" || !Number.isInteger(academicYear)) {
      setErrorMessage("年度を入力してください。");
      return;
    }
    if (newStartsAt === "" || newEndsAt === "") {
      setErrorMessage("開始日・終了日を入力してください。");
      return;
    }
    setIsCreating(true);
    try {
      const res = await apiFetch("/admin/recruitment-terms", session, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          academic_year: academicYear,
          starts_at: newStartsAt,
          ends_at: newEndsAt,
          status: newStatus,
        }),
      });
      if (!res.ok) {
        setErrorMessage(await extractErrorDetail(res));
        return;
      }
      const created: AdminRecruitmentTerm = {
        ...((await res.json()) as Omit<
          AdminRecruitmentTerm,
          "target_grades_summary"
        >),
        target_grades_summary: "未設定",
      };
      setTerms((prev) =>
        [...prev, created].sort((a, b) => {
          if (a.academic_year !== b.academic_year) {
            return b.academic_year - a.academic_year;
          }
          return a.starts_at.localeCompare(b.starts_at);
        }),
      );
      if (allSeminars.length > 0) {
        try {
          await applyBulkTargetGrades(created.id, newBulkTargetGrades);
          const summary =
            newBulkTargetGrades.length === 0
              ? "対象学年なし"
              : newBulkTargetGrades.join(", ");
          setTerms((prev) =>
            prev.map((t) =>
              t.id === created.id ? { ...t, target_grades_summary: summary } : t,
            ),
          );
        } catch {
          setErrorMessage(
            "募集ラウンドは作成しましたが、対象学年の一括設定に失敗しました。「ゼミ別設定」から個別に確認してください。",
          );
        }
      }
      resetCreateForm();
    } catch {
      setErrorMessage("通信に失敗しました。時間をおいて再度お試しください。");
    } finally {
      setIsCreating(false);
    }
  }

  function startEdit(term: AdminRecruitmentTerm): void {
    setEditingId(term.id);
    setEditStartsAt(term.starts_at);
    setEditEndsAt(term.ends_at);
    setEditStatus(term.status);
    setErrorMessage(null);
  }

  function cancelEdit(): void {
    setEditingId(null);
  }

  async function handleSaveEdit(termId: string): Promise<void> {
    setErrorMessage(null);
    if (editStartsAt === "" || editEndsAt === "") {
      setErrorMessage("開始日・終了日を入力してください。");
      return;
    }
    setIsSavingEdit(true);
    try {
      const res = await apiFetch(
        `/admin/recruitment-terms/${termId}`,
        session,
        {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            starts_at: editStartsAt,
            ends_at: editEndsAt,
            status: editStatus,
          }),
        },
      );
      if (!res.ok) {
        setErrorMessage(await extractErrorDetail(res));
        return;
      }
      const updated = (await res.json()) as Omit<
        AdminRecruitmentTerm,
        "target_grades_summary"
      >;
      setTerms((prev) =>
        prev.map((t) => (t.id === termId ? { ...t, ...updated } : t)),
      );
      setEditingId(null);
    } catch {
      setErrorMessage("通信に失敗しました。時間をおいて再度お試しください。");
    } finally {
      setIsSavingEdit(false);
    }
  }

  async function handleSelectTerm(termId: string): Promise<void> {
    setErrorMessage(null);
    if (selectedTermId === termId) {
      setSelectedTermId(null);
      return;
    }
    setSelectedTermId(termId);
    setIsLoadingRecruitments(true);
    try {
      const res = await apiFetch(
        `/admin/recruitment-terms/${termId}/seminars`,
        session,
        { cache: "no-store" },
      );
      if (!res.ok) {
        setErrorMessage(await extractErrorDetail(res));
        setRecruitments([]);
        setRecruitmentInputs({});
        return;
      }
      const data = (await res.json()) as AdminSeminarRecruitment[];
      setRecruitments(data);
      setRecruitmentInputs(buildRecruitmentInputs(data));
    } catch {
      setErrorMessage("通信に失敗しました。時間をおいて再度お試しください。");
      setRecruitments([]);
      setRecruitmentInputs({});
    } finally {
      setIsLoadingRecruitments(false);
    }
  }

  function updateRecruitmentInput(
    seminarId: string,
    patch: Partial<RecruitmentInput>,
  ): void {
    setRecruitmentInputs((prev) => ({
      ...prev,
      [seminarId]: {
        ...(prev[seminarId] ?? defaultRecruitmentInput()),
        ...patch,
      },
    }));
  }

  function toggleTargetGrade(seminarId: string, grade: string): void {
    const current = recruitmentInputs[seminarId]?.targetGrades ?? [
      ...GRADE_OPTIONS,
    ];
    const next = current.includes(grade)
      ? current.filter((g) => g !== grade)
      : [...current, grade];
    // 常にGRADE_OPTIONS順(B1〜B4)で保存し、表示順がチェックした順に
    // 左右されないようにする。
    const targetGrades = GRADE_OPTIONS.filter((g) => next.includes(g));
    updateRecruitmentInput(seminarId, { targetGrades });
  }

  async function handleSaveAllRecruitments(): Promise<void> {
    if (!selectedTermId) {
      return;
    }
    setErrorMessage(null);

    // 送信前に全ゼミの定員をまとめて検証する。1件でも不正なら送信しない。
    const payloads: {
      seminarId: string;
      capacity: number;
      grades: string[];
    }[] = [];
    for (const r of recruitments) {
      const input =
        recruitmentInputs[r.seminar_id] ?? defaultRecruitmentInput();
      if (input.capacity.trim() === "") {
        setErrorMessage(`「${r.seminar_name}」の募集人数を入力してください。`);
        return;
      }
      const capacity = Number(input.capacity);
      if (!Number.isInteger(capacity) || capacity < 0) {
        setErrorMessage(
          `「${r.seminar_name}」の募集人数は0以上の整数で入力してください。`,
        );
        return;
      }
      payloads.push({
        seminarId: r.seminar_id,
        capacity,
        grades: input.targetGrades,
      });
    }

    // 対象学年が未選択のゼミがあれば、まとめて1回だけ確認する。
    const emptyGradeNames = recruitments
      .filter(
        (r) =>
          (recruitmentInputs[r.seminar_id] ?? defaultRecruitmentInput())
            .targetGrades.length === 0,
      )
      .map((r) => r.seminar_name);
    if (emptyGradeNames.length > 0) {
      const confirmed = window.confirm(
        `対象学年が1つも選択されていないゼミがあります(${emptyGradeNames.join(
          "、",
        )})。これらを募集していない状態にして保存します。よろしいですか?`,
      );
      if (!confirmed) {
        return;
      }
    }

    setIsSavingRecruitments(true);
    try {
      const results = await Promise.all(
        payloads.map(async ({ seminarId, capacity, grades }) => {
          const res = await apiFetch(
            `/admin/recruitment-terms/${selectedTermId}/seminars/${seminarId}`,
            session,
            {
              method: "PUT",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({
                capacity,
                target_grades: grades,
              }),
            },
          );
          if (!res.ok) {
            return { seminarId, ok: false as const };
          }
          const updated = (await res.json()) as AdminSeminarRecruitment;
          return { seminarId, ok: true as const, updated };
        }),
      );

      // 成功したゼミの結果だけ反映する。
      const succeeded = results.filter(
        (
          r,
        ): r is {
          seminarId: string;
          ok: true;
          updated: AdminSeminarRecruitment;
        } => r.ok,
      );
      if (succeeded.length > 0) {
        const updatedById = new Map(
          succeeded.map((r) => [r.seminarId, r.updated]),
        );
        const mergedRecruitments = recruitments.map(
          (r) => updatedById.get(r.seminar_id) ?? r,
        );
        setRecruitments(mergedRecruitments);
        if (selectedTermId) {
          const summary = summarizeTargetGrades(mergedRecruitments);
          setTerms((prev) =>
            prev.map((t) =>
              t.id === selectedTermId
                ? { ...t, target_grades_summary: summary }
                : t,
            ),
          );
        }
        setRecruitmentInputs((prev) => {
          const next = { ...prev };
          for (const { seminarId, updated } of succeeded) {
            next[seminarId] = {
              capacity:
                updated.capacity === null ? "" : String(updated.capacity),
              targetGrades: updated.target_grades ?? [...GRADE_OPTIONS],
            };
          }
          return next;
        });
      }

      const failedCount = results.length - succeeded.length;
      if (failedCount > 0) {
        setErrorMessage(`${failedCount}件のゼミの保存に失敗しました。`);
      }
    } catch {
      setErrorMessage("通信に失敗しました。時間をおいて再度お試しください。");
    } finally {
      setIsSavingRecruitments(false);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      {errorMessage && (
        <p className="rounded-2xl border-2 border-red-300 bg-white p-4 text-sm text-red-600 shadow-sm">
          {errorMessage}
        </p>
      )}

      {isCreateFormOpen ? (
        <section className="rounded-2xl border-2 border-[#add8e6] bg-white p-4 shadow-sm shadow-[#add8e6]/30">
          <h2 className="font-semibold text-zinc-800">新規募集ラウンド作成</h2>
          <div className="mt-3 flex flex-col gap-2">
            <label className="flex flex-col gap-1 text-sm">
              年度
              <input
                type="number"
                value={newAcademicYear}
                onChange={(e) => setNewAcademicYear(e.target.value)}
                placeholder="2027"
                className="w-32 rounded-lg border border-[#add8e6]/60 bg-white px-3 py-2 text-sm text-zinc-800 focus:border-[#add8e6] focus:outline-none focus-visible:ring-2 focus-visible:ring-[#add8e6]/50"
              />
            </label>
            <div className="flex flex-wrap gap-2">
              <div className="flex flex-col gap-1 text-sm">
                <span>開始日</span>
                <SkyDatePicker
                  value={newStartsAt}
                  onChange={setNewStartsAt}
                  ariaLabel="開始日"
                  className="w-44"
                />
              </div>
              <div className="flex flex-col gap-1 text-sm">
                <span>終了日</span>
                <SkyDatePicker
                  value={newEndsAt}
                  onChange={setNewEndsAt}
                  ariaLabel="終了日"
                  className="w-44"
                />
              </div>
              <div className="flex flex-col gap-1 text-sm">
                <span>状態</span>
                <SkySelect
                  value={newStatus}
                  options={STATUS_OPTIONS}
                  onChange={(next) =>
                    setNewStatus(next as AdminRecruitmentTerm["status"])
                  }
                  ariaLabel="状態"
                  className="w-40"
                />
              </div>
            </div>
            {newStartsAt !== "" && newEndsAt !== "" && (
              <p className="text-xs text-zinc-500">
                確認: {formatPeriod(newStartsAt, newEndsAt)}
              </p>
            )}
            {allSeminars.length > 0 && (
              <div className="flex flex-col gap-1">
                <p className="text-sm text-zinc-500">対象学年</p>
                <div className="flex flex-wrap gap-3">
                  {GRADE_OPTIONS.map((grade) => (
                    <label
                      key={grade}
                      className="flex items-center gap-1.5 text-sm"
                    >
                      <input
                        type="checkbox"
                        checked={newBulkTargetGrades.includes(grade)}
                        onChange={() => toggleNewBulkTargetGrade(grade)}
                        className="h-4 w-4 accent-[#add8e6]"
                      />
                      {grade}
                    </label>
                  ))}
                </div>
              </div>
            )}
            <div className="flex gap-2">
              <button
                type="button"
                onClick={handleCreate}
                disabled={isCreating}
                className="self-start rounded-full bg-[#add8e6] px-4 py-2 text-sm font-semibold text-sky-950 shadow-sm transition-all hover:bg-[#9bcfe0] hover:shadow active:translate-y-px disabled:cursor-not-allowed disabled:opacity-50 focus:outline-none focus-visible:ring-4 focus-visible:ring-[#add8e6]/50"
              >
                {isCreating ? "作成中..." : "作成する"}
              </button>
              <button
                type="button"
                onClick={cancelCreate}
                disabled={isCreating}
                className="self-start rounded-full border border-[#add8e6]/60 px-4 py-2 text-sm font-medium text-zinc-700 transition-colors hover:bg-[#add8e6]/10 disabled:cursor-not-allowed disabled:opacity-50"
              >
                キャンセル
              </button>
            </div>
          </div>
        </section>
      ) : (
        <button
          type="button"
          onClick={openCreateForm}
          className="self-start rounded-full bg-[#add8e6] px-4 py-2 text-sm font-semibold text-sky-950 shadow-sm transition-all hover:bg-[#9bcfe0] hover:shadow active:translate-y-px focus:outline-none focus-visible:ring-4 focus-visible:ring-[#add8e6]/50"
        >
          + 新規募集ラウンドを作成
        </button>
      )}

      <div className="flex flex-col gap-4">
        {terms.length === 0 ? (
          <p className="text-sm text-zinc-400">
            募集ラウンドがまだありません。
          </p>
        ) : (
          terms.map((term) => {
            const isEditing = editingId === term.id;
            const isSelected = selectedTermId === term.id;

            return (
              <section
                key={term.id}
                className="rounded-2xl border-2 border-[#add8e6] bg-white p-4 shadow-sm shadow-[#add8e6]/30"
              >
                {isEditing ? (
                  <div className="flex flex-col gap-2">
                    <p className="text-sm text-zinc-500">
                      {term.academic_year}年度
                    </p>
                    <div className="flex flex-wrap gap-2">
                      <div className="flex flex-col gap-1 text-sm">
                        <span>開始日</span>
                        <SkyDatePicker
                          value={editStartsAt}
                          onChange={setEditStartsAt}
                          ariaLabel="開始日"
                          className="w-44"
                        />
                      </div>
                      <div className="flex flex-col gap-1 text-sm">
                        <span>終了日</span>
                        <SkyDatePicker
                          value={editEndsAt}
                          onChange={setEditEndsAt}
                          ariaLabel="終了日"
                          className="w-44"
                        />
                      </div>
                      <div className="flex flex-col gap-1 text-sm">
                        <span>状態</span>
                        <SkySelect
                          value={editStatus}
                          options={STATUS_OPTIONS}
                          onChange={(next) =>
                            setEditStatus(
                              next as AdminRecruitmentTerm["status"],
                            )
                          }
                          ariaLabel="状態"
                          className="w-40"
                        />
                      </div>
                    </div>
                    {editStartsAt !== "" && editEndsAt !== "" && (
                      <p className="text-xs text-zinc-500">
                        確認: {formatPeriod(editStartsAt, editEndsAt)}
                      </p>
                    )}
                    <div className="flex gap-2">
                      <button
                        type="button"
                        onClick={() => handleSaveEdit(term.id)}
                        disabled={isSavingEdit}
                        className="rounded-full bg-[#add8e6] px-4 py-2 text-sm font-semibold text-sky-950 shadow-sm transition-all hover:bg-[#9bcfe0] hover:shadow active:translate-y-px disabled:cursor-not-allowed disabled:opacity-50 focus:outline-none focus-visible:ring-4 focus-visible:ring-[#add8e6]/50"
                      >
                        {isSavingEdit ? "保存中..." : "保存する"}
                      </button>
                      <button
                        type="button"
                        onClick={cancelEdit}
                        disabled={isSavingEdit}
                        className="rounded-full border border-[#add8e6]/60 px-4 py-2 text-sm font-medium text-zinc-700 transition-colors hover:bg-[#add8e6]/10 disabled:cursor-not-allowed disabled:opacity-50"
                      >
                        キャンセル
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <p className="font-semibold text-zinc-800">
                        {term.academic_year}年度
                        <span className="ml-2 text-xs font-normal text-zinc-500">
                          {statusLabel(term)}
                        </span>
                      </p>
                      <p className="mt-1 text-sm text-zinc-600">
                        {formatPeriod(term.starts_at, term.ends_at)}
                      </p>
                      <p className="mt-1 text-sm text-zinc-600">
                        対象学年: {term.target_grades_summary}
                      </p>
                    </div>
                    <div className="flex shrink-0 gap-2">
                      <button
                        type="button"
                        onClick={() => startEdit(term)}
                        className="rounded-full border border-[#add8e6]/60 px-3 py-1.5 text-xs font-medium text-zinc-700 transition-colors hover:bg-[#add8e6]/10"
                      >
                        編集
                      </button>
                      <button
                        type="button"
                        onClick={() => handleSelectTerm(term.id)}
                        className="rounded-full border border-[#add8e6]/60 px-3 py-1.5 text-xs font-medium text-zinc-700 transition-colors hover:bg-[#add8e6]/10"
                      >
                        {isSelected ? "ゼミ別設定を閉じる" : "ゼミ別設定"}
                      </button>
                    </div>
                  </div>
                )}

                {isSelected && (
                  <div className="mt-3 flex flex-col gap-2 border-t border-[#add8e6]/40 pt-3">
                    <p className="text-sm text-zinc-500">
                      ゼミ別の定員・対象学年
                    </p>
                    {isLoadingRecruitments ? (
                      <p className="text-sm text-zinc-400">読み込み中...</p>
                    ) : (
                      recruitments.map((r) => {
                        const input =
                          recruitmentInputs[r.seminar_id] ??
                          defaultRecruitmentInput();
                        return (
                          <div
                            key={r.seminar_id}
                            className="flex flex-col gap-1 rounded-lg border border-[#add8e6]/60 bg-[#add8e6]/[.06] p-3"
                          >
                            <p className="text-sm font-medium text-zinc-800">
                              {r.seminar_name}
                            </p>
                            <div className="flex flex-wrap items-center gap-2">
                              <input
                                type="number"
                                min={0}
                                value={input.capacity}
                                onChange={(e) =>
                                  updateRecruitmentInput(r.seminar_id, {
                                    capacity: e.target.value,
                                  })
                                }
                                placeholder="人数"
                                className="w-24 rounded-lg border border-[#add8e6]/60 bg-white px-3 py-1.5 text-sm text-zinc-800 focus:border-[#add8e6] focus:outline-none focus-visible:ring-2 focus-visible:ring-[#add8e6]/50"
                              />
                              {GRADE_OPTIONS.map((grade) => (
                                <label
                                  key={grade}
                                  className="flex items-center gap-1.5 text-sm"
                                >
                                  <input
                                    type="checkbox"
                                    checked={input.targetGrades.includes(grade)}
                                    onChange={() =>
                                      toggleTargetGrade(r.seminar_id, grade)
                                    }
                                    className="h-4 w-4 accent-[#add8e6]"
                                  />
                                  {grade}
                                </label>
                              ))}
                            </div>
                          </div>
                        );
                      })
                    )}
                    <p className="text-xs text-zinc-400">
                      対象学年をすべて外すと、そのゼミは募集していない扱いになります。
                    </p>
                    {!isLoadingRecruitments && recruitments.length > 0 && (
                      <div className="flex justify-end pt-1">
                        <button
                          type="button"
                          onClick={handleSaveAllRecruitments}
                          disabled={isSavingRecruitments}
                          className="rounded-full bg-[#add8e6] px-4 py-2 text-sm font-semibold text-sky-950 shadow-sm transition-all hover:bg-[#9bcfe0] active:translate-y-px disabled:cursor-not-allowed disabled:opacity-50 focus:outline-none focus-visible:ring-4 focus-visible:ring-[#add8e6]/50"
                        >
                          {isSavingRecruitments ? "保存中..." : "保存する"}
                        </button>
                      </div>
                    )}
                  </div>
                )}
              </section>
            );
          })
        )}
      </div>
    </div>
  );
}
