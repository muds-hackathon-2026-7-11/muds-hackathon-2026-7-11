"use client";

import { useSession } from "next-auth/react";
import { useState } from "react";
import { apiFetch } from "@/lib/api-client";

export type AdminRecruitmentTerm = {
  id: string;
  academic_year: number;
  starts_at: string;
  ends_at: string;
  status: "preparing" | "open" | "closed";
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
  const [savingSeminarId, setSavingSeminarId] = useState<string | null>(null);

  function openCreateForm(): void {
    setIsCreateFormOpen(true);
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
      const created = (await res.json()) as AdminRecruitmentTerm;
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
      const updated = (await res.json()) as AdminRecruitmentTerm;
      setTerms((prev) => prev.map((t) => (t.id === termId ? updated : t)));
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

  async function handleSaveRecruitment(seminarId: string): Promise<void> {
    if (!selectedTermId) {
      return;
    }
    const input = recruitmentInputs[seminarId] ?? defaultRecruitmentInput();
    setErrorMessage(null);
    if (input.capacity.trim() === "") {
      setErrorMessage("募集人数を入力してください。");
      return;
    }
    const capacity = Number(input.capacity);
    if (!Number.isInteger(capacity) || capacity < 0) {
      setErrorMessage("募集人数は0以上の整数で入力してください。");
      return;
    }
    if (input.targetGrades.length === 0) {
      const seminarName =
        recruitments.find((r) => r.seminar_id === seminarId)?.seminar_name ??
        "このゼミ";
      const confirmed = window.confirm(
        `対象学年が1つも選択されていません。「${seminarName}」を募集していない状態にして保存します。よろしいですか?`,
      );
      if (!confirmed) {
        return;
      }
    }
    setSavingSeminarId(seminarId);
    try {
      const res = await apiFetch(
        `/admin/recruitment-terms/${selectedTermId}/seminars/${seminarId}`,
        session,
        {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            capacity,
            target_grades: input.targetGrades,
          }),
        },
      );
      if (!res.ok) {
        setErrorMessage(await extractErrorDetail(res));
        return;
      }
      const updated = (await res.json()) as AdminSeminarRecruitment;
      setRecruitments((prev) =>
        prev.map((r) => (r.seminar_id === seminarId ? updated : r)),
      );
      setRecruitmentInputs((prev) => ({
        ...prev,
        [seminarId]: {
          capacity: updated.capacity === null ? "" : String(updated.capacity),
          targetGrades: updated.target_grades ?? [...GRADE_OPTIONS],
        },
      }));
    } catch {
      setErrorMessage("通信に失敗しました。時間をおいて再度お試しください。");
    } finally {
      setSavingSeminarId(null);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      {errorMessage && (
        <p className="rounded-lg border border-black/[.08] p-4 text-sm dark:border-white/[.145]">
          {errorMessage}
        </p>
      )}

      {isCreateFormOpen ? (
        <section className="rounded-lg border border-black/[.08] p-4 dark:border-white/[.145]">
          <h2 className="font-semibold">新規募集ラウンド作成</h2>
          <div className="mt-3 flex flex-col gap-2">
            <label className="flex flex-col gap-1 text-sm">
              年度
              <input
                type="number"
                value={newAcademicYear}
                onChange={(e) => setNewAcademicYear(e.target.value)}
                placeholder="2027"
                className="w-32 rounded-lg border border-black/[.08] bg-background px-3 py-2 text-sm dark:border-white/[.145]"
              />
            </label>
            <div className="flex flex-wrap gap-2">
              <label className="flex flex-col gap-1 text-sm">
                開始日
                <input
                  type="date"
                  value={newStartsAt}
                  onChange={(e) => setNewStartsAt(e.target.value)}
                  className="rounded-lg border border-black/[.08] bg-background px-3 py-2 text-sm dark:border-white/[.145]"
                />
              </label>
              <label className="flex flex-col gap-1 text-sm">
                終了日
                <input
                  type="date"
                  value={newEndsAt}
                  onChange={(e) => setNewEndsAt(e.target.value)}
                  className="rounded-lg border border-black/[.08] bg-background px-3 py-2 text-sm dark:border-white/[.145]"
                />
              </label>
              <label className="flex flex-col gap-1 text-sm">
                状態
                <select
                  value={newStatus}
                  onChange={(e) =>
                    setNewStatus(
                      e.target.value as AdminRecruitmentTerm["status"],
                    )
                  }
                  className="rounded-lg border border-black/[.08] bg-background px-3 py-2 text-sm dark:border-white/[.145]"
                >
                  <option value="preparing">準備中</option>
                  <option value="open">募集中</option>
                  <option value="closed">終了</option>
                </select>
              </label>
            </div>
            {newStartsAt !== "" && newEndsAt !== "" && (
              <p className="text-xs text-foreground/60">
                確認: {formatPeriod(newStartsAt, newEndsAt)}
              </p>
            )}
            {allSeminars.length > 0 && (
              <div className="flex flex-col gap-1">
                <p className="text-sm text-foreground/60">対象学年</p>
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
                className="self-start rounded-full bg-foreground px-4 py-2 text-sm font-medium text-background hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {isCreating ? "作成中..." : "作成する"}
              </button>
              <button
                type="button"
                onClick={cancelCreate}
                disabled={isCreating}
                className="self-start rounded-full border border-black/[.08] px-4 py-2 text-sm font-medium hover:bg-black/[.04] disabled:cursor-not-allowed disabled:opacity-50 dark:border-white/[.145] dark:hover:bg-white/[.08]"
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
          className="self-start rounded-full bg-foreground px-4 py-2 text-sm font-medium text-background hover:opacity-90"
        >
          + 新規募集ラウンドを作成
        </button>
      )}

      <div className="flex flex-col gap-4">
        {terms.length === 0 ? (
          <p className="text-sm text-foreground/40">
            募集ラウンドがまだありません。
          </p>
        ) : (
          terms.map((term) => {
            const isEditing = editingId === term.id;
            const isSelected = selectedTermId === term.id;

            return (
              <section
                key={term.id}
                className="rounded-lg border border-black/[.08] p-4 dark:border-white/[.145]"
              >
                {isEditing ? (
                  <div className="flex flex-col gap-2">
                    <p className="text-sm text-foreground/60">
                      {term.academic_year}年度
                    </p>
                    <div className="flex flex-wrap gap-2">
                      <label className="flex flex-col gap-1 text-sm">
                        開始日
                        <input
                          type="date"
                          value={editStartsAt}
                          onChange={(e) => setEditStartsAt(e.target.value)}
                          className="rounded-lg border border-black/[.08] bg-background px-3 py-2 text-sm dark:border-white/[.145]"
                        />
                      </label>
                      <label className="flex flex-col gap-1 text-sm">
                        終了日
                        <input
                          type="date"
                          value={editEndsAt}
                          onChange={(e) => setEditEndsAt(e.target.value)}
                          className="rounded-lg border border-black/[.08] bg-background px-3 py-2 text-sm dark:border-white/[.145]"
                        />
                      </label>
                      <label className="flex flex-col gap-1 text-sm">
                        状態
                        <select
                          value={editStatus}
                          onChange={(e) =>
                            setEditStatus(
                              e.target.value as AdminRecruitmentTerm["status"],
                            )
                          }
                          className="rounded-lg border border-black/[.08] bg-background px-3 py-2 text-sm dark:border-white/[.145]"
                        >
                          <option value="preparing">準備中</option>
                          <option value="open">募集中</option>
                          <option value="closed">終了</option>
                        </select>
                      </label>
                    </div>
                    {editStartsAt !== "" && editEndsAt !== "" && (
                      <p className="text-xs text-foreground/60">
                        確認: {formatPeriod(editStartsAt, editEndsAt)}
                      </p>
                    )}
                    <div className="flex gap-2">
                      <button
                        type="button"
                        onClick={() => handleSaveEdit(term.id)}
                        disabled={isSavingEdit}
                        className="rounded-full bg-foreground px-4 py-2 text-sm font-medium text-background hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
                      >
                        {isSavingEdit ? "保存中..." : "保存する"}
                      </button>
                      <button
                        type="button"
                        onClick={cancelEdit}
                        disabled={isSavingEdit}
                        className="rounded-full border border-black/[.08] px-4 py-2 text-sm font-medium hover:bg-black/[.04] disabled:cursor-not-allowed disabled:opacity-50 dark:border-white/[.145] dark:hover:bg-white/[.08]"
                      >
                        キャンセル
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <p className="font-semibold">
                        {term.academic_year}年度
                        <span className="ml-2 text-xs font-normal text-foreground/60">
                          {statusLabel(term)}
                        </span>
                      </p>
                      <p className="mt-1 text-sm text-foreground/70">
                        {formatPeriod(term.starts_at, term.ends_at)}
                      </p>
                      <p className="mt-1 text-xs text-foreground/40">
                        ID(配属結果CSVのterm_id列に使用):{" "}
                        <code className="select-all">{term.id}</code>
                      </p>
                    </div>
                    <div className="flex shrink-0 gap-2">
                      <button
                        type="button"
                        onClick={() => startEdit(term)}
                        className="rounded-full border border-black/[.08] px-3 py-1.5 text-xs font-medium hover:bg-black/[.04] dark:border-white/[.145] dark:hover:bg-white/[.08]"
                      >
                        編集
                      </button>
                      <button
                        type="button"
                        onClick={() => handleSelectTerm(term.id)}
                        className="rounded-full border border-black/[.08] px-3 py-1.5 text-xs font-medium hover:bg-black/[.04] dark:border-white/[.145] dark:hover:bg-white/[.08]"
                      >
                        {isSelected ? "ゼミ別設定を閉じる" : "ゼミ別設定"}
                      </button>
                    </div>
                  </div>
                )}

                {isSelected && (
                  <div className="mt-3 flex flex-col gap-2 border-t border-black/[.08] pt-3 dark:border-white/[.145]">
                    <p className="text-sm text-foreground/60">
                      ゼミ別の定員・対象学年
                    </p>
                    {isLoadingRecruitments ? (
                      <p className="text-sm text-foreground/40">
                        読み込み中...
                      </p>
                    ) : (
                      recruitments.map((r) => {
                        const input =
                          recruitmentInputs[r.seminar_id] ??
                          defaultRecruitmentInput();
                        return (
                          <div
                            key={r.seminar_id}
                            className="flex flex-col gap-1 rounded-lg border border-black/[.08] p-3 dark:border-white/[.145]"
                          >
                            <p className="text-sm font-medium">
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
                                className="w-24 rounded-lg border border-black/[.08] bg-background px-3 py-1.5 text-sm dark:border-white/[.145]"
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
                                  />
                                  {grade}
                                </label>
                              ))}
                              <button
                                type="button"
                                onClick={() =>
                                  handleSaveRecruitment(r.seminar_id)
                                }
                                disabled={savingSeminarId === r.seminar_id}
                                className="rounded-full border border-black/[.08] px-3 py-1.5 text-xs font-medium hover:bg-black/[.04] disabled:cursor-not-allowed disabled:opacity-50 dark:border-white/[.145] dark:hover:bg-white/[.08]"
                              >
                                {savingSeminarId === r.seminar_id
                                  ? "保存中..."
                                  : "保存する"}
                              </button>
                            </div>
                          </div>
                        );
                      })
                    )}
                    <p className="text-xs text-foreground/40">
                      対象学年をすべて外すと、そのゼミは募集していない扱いになります。
                    </p>
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
