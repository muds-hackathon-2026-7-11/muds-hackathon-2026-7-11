"use client";

import { useSession } from "next-auth/react";
import { useCallback, useRef, useState } from "react";
import { apiFetch } from "@/lib/api-client";

// バックエンドは画面を開いた後に募集期間が終了した場合、保存・提出時に
// このエラーを返す(現在募集中の期間がないため)。生のエラー文言のままだと
// 何をすればいいか伝わりにくいので、ページ更新を促す文言に置き換える。
const TERM_CLOSED_DETAIL = "現在募集中の期間がありません。";
const TERM_CLOSED_MESSAGE = "締切が過ぎました。ページを更新してください。";

async function extractErrorDetail(res: Response): Promise<string> {
  try {
    const body = (await res.json()) as { detail?: string };
    if (body.detail === TERM_CLOSED_DETAIL) {
      return TERM_CLOSED_MESSAGE;
    }
    return body.detail ?? "エラーが発生しました。";
  } catch {
    return "エラーが発生しました。";
  }
}

export type Seminar = {
  id: string;
  name: string;
};

export type ApplicationChoice = {
  seminar_id: string;
  priority: number;
  reason: string;
  match_score: number | null;
  match_feedback: Record<string, unknown> | null;
};

export type ApplicationFormData = {
  id: string | null;
  status: "draft" | "submitted";
  submitted_at: string | null;
  choices: ApplicationChoice[];
  is_editable: boolean;
};

type Slot = {
  seminarId: string;
  reason: string;
};

const PRIORITY_LABELS = ["第1志望", "第2志望", "第3志望"] as const;

function toSlots(choices: ApplicationChoice[]): [Slot, Slot, Slot] {
  const slots: [Slot, Slot, Slot] = [
    { seminarId: "", reason: "" },
    { seminarId: "", reason: "" },
    { seminarId: "", reason: "" },
  ];
  for (const choice of choices) {
    const index = choice.priority - 1;
    if (index >= 0 && index < 3) {
      slots[index] = { seminarId: choice.seminar_id, reason: choice.reason };
    }
  }
  return slots;
}

function formatDateTime(value: string | null): string {
  if (!value) {
    return "";
  }
  return new Date(value).toLocaleString("ja-JP", {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

type ApplicationFormProps = {
  seminars: Seminar[];
  initialApplication: ApplicationFormData;
};

export function ApplicationForm({
  seminars,
  initialApplication,
}: ApplicationFormProps) {
  const { data: session } = useSession();
  const [slots, setSlots] = useState<[Slot, Slot, Slot]>(() =>
    toSlots(initialApplication.choices),
  );
  const [submittedAt, setSubmittedAt] = useState(
    initialApplication.submitted_at,
  );
  const isEditable = initialApplication.is_editable;
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isReverting, setIsReverting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [submittedMessage, setSubmittedMessage] = useState<string | null>(null);
  // 提出済みの内容を誤って書き換えないよう、まず読み取り専用で表示し、
  // 「編集する」を押すまで入力できないようにする。募集期間外の場合は
  // 編集する自体を出さない(読み取り専用のまま)。
  const [isLocked, setIsLocked] = useState(
    !initialApplication.is_editable ||
      initialApplication.status === "submitted",
  );
  const [snapshotSlots, setSnapshotSlots] = useState<[Slot, Slot, Slot] | null>(
    null,
  );
  // 編集中は自動保存しないため、通常は「戻る」時にサーバーへ送るものは何もない
  // (何もPUTしていない)。ただし「提出する」を押した際にPUTだけ成功し、直後の
  // POST(/submit)が失敗するケースがあり、その場合はサーバー側が編集後の内容
  // で上書きされたまま残ってしまう。このrefはその「サーバー側が編集前と
  // 食い違っている」状態だけを追跡し、戻る時に本当に必要な場合だけサーバーへ
  // 書き戻す(毎回PUTすると提出日時が更新されたりマッチ度が消えたりするため、
  // 不要な時は絶対に呼ばない)。
  const serverDirtySinceEdit = useRef(false);

  function selectedSeminarIdsExcept(index: number): Set<string> {
    return new Set(
      slots
        .filter((_, i) => i !== index)
        .map((slot) => slot.seminarId)
        .filter((id) => id !== ""),
    );
  }

  function updateSlot(index: number, patch: Partial<Slot>): void {
    setSlots((prev) => {
      const next = [...prev] as [Slot, Slot, Slot];
      next[index] = { ...next[index], ...patch };
      return next;
    });
  }

  function buildPayloadChoices() {
    return slots
      .map((slot, index) => ({ slot, priority: index + 1 }))
      .filter(({ slot }) => slot.seminarId !== "")
      .map(({ slot, priority }) => ({
        seminar_id: slot.seminarId,
        priority,
        reason: slot.reason,
      }));
  }

  function missingReasonLabels(): string[] {
    return slots
      .map((slot, index) => ({ slot, index }))
      .filter(({ slot }) => slot.seminarId !== "" && slot.reason.trim() === "")
      .map(({ index }) => PRIORITY_LABELS[index]);
  }

  // 保存(PUT)本体。バリデーションはせず、渡された内容をそのまま保存する。
  // 呼び出し元は「提出する」と、提出失敗後の「戻る」(サーバー側が編集後の
  // 内容のまま残っている場合のみ)の2箇所。編集中の入力そのものからは
  // 呼ばれない(自動保存はしない)。保存対象を引数で明示的に受け取るのは、
  // 「戻る」の時は現在のslots stateではなくスナップショットを送りたいため。
  //
  // 注意: バックエンドのPUTは、既に提出済み(status=submitted)のフォームに
  // 対しては内容が変わっていなくても提出日時(submitted_at)を更新し、
  // match_score/match_feedbackを常にクリアする。呼ぶたびにこの副作用が
  // 起きるため、本当に必要な時(=serverDirtySinceEdit)以外は呼ばないこと。
  const persistChoices = useCallback(
    async (slotsToSave: [Slot, Slot, Slot]): Promise<boolean> => {
      try {
        const res = await apiFetch("/applications/me", session, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            choices: slotsToSave
              .map((slot, index) => ({ slot, priority: index + 1 }))
              .filter(({ slot }) => slot.seminarId !== "")
              .map(({ slot, priority }) => ({
                seminar_id: slot.seminarId,
                priority,
                reason: slot.reason,
              })),
          }),
        });
        if (!res.ok) {
          setErrorMessage(await extractErrorDetail(res));
          return false;
        }
        const data = (await res.json()) as ApplicationFormData;
        setSubmittedAt(data.submitted_at);
        setSlots(toSlots(data.choices));
        return true;
      } catch {
        setErrorMessage("通信に失敗しました。時間をおいて再度お試しください。");
        return false;
      }
    },
    [session],
  );

  async function handleSubmitClick(): Promise<void> {
    setErrorMessage(null);
    setSubmittedMessage(null);

    if (buildPayloadChoices().length === 0) {
      setErrorMessage("志望を1件以上入力してください。");
      return;
    }
    const missing = missingReasonLabels();
    if (missing.length > 0) {
      setErrorMessage(`${missing.join("・")}の志望理由が未入力です。`);
      return;
    }

    setIsSubmitting(true);
    try {
      const saved = await persistChoices(slots);
      if (!saved) {
        return;
      }
      // ここでPUTが成功した時点でサーバー側は編集後の内容になっている。
      // この後のPOSTが失敗すると、サーバー側は編集前のスナップショットと
      // 食い違ったまま残るため、「戻る」で必ず書き戻す必要がある。
      serverDirtySinceEdit.current = true;

      const res = await apiFetch("/applications/me/submit", session, {
        method: "POST",
      });
      if (!res.ok) {
        setErrorMessage(await extractErrorDetail(res));
        return;
      }
      const data = (await res.json()) as ApplicationFormData;
      setSubmittedAt(data.submitted_at);
      setSlots(toSlots(data.choices));
      setSubmittedMessage("志望を提出しました。");
      setIsLocked(true);
      setSnapshotSlots(null);
      serverDirtySinceEdit.current = false;
    } catch {
      setErrorMessage("通信に失敗しました。時間をおいて再度お試しください。");
    } finally {
      setIsSubmitting(false);
    }
  }

  function handleEditClick(): void {
    setSnapshotSlots(slots);
    serverDirtySinceEdit.current = false;
    setIsLocked(false);
    setErrorMessage(null);
    setSubmittedMessage(null);
  }

  // 通常(提出を試みていない、または提出が最後まで成功している)は、編集中に
  // サーバーへ何も送っていないため、戻るはローカルの表示を戻すだけでよい。
  // 「提出する」でPUTだけ成功しPOSTが失敗した場合(serverDirtySinceEdit)だけ、
  // サーバー側が編集後の内容のままなので、スナップショットを明示的に書き戻す。
  // 毎回PUTしないのは、PUTのたびに提出日時が更新されたりマッチ度が消えたり
  // する副作用があり、何も送る必要が無い時にそれを起こしたくないため。
  async function handleRevertClick(): Promise<void> {
    if (!snapshotSlots) {
      setIsLocked(true);
      return;
    }

    if (!serverDirtySinceEdit.current) {
      setSlots(snapshotSlots);
      setSnapshotSlots(null);
      setIsLocked(true);
      setErrorMessage(null);
      return;
    }

    setIsReverting(true);
    setErrorMessage(null);
    try {
      const ok = await persistChoices(snapshotSlots);
      if (!ok) {
        return;
      }
      serverDirtySinceEdit.current = false;
      setSnapshotSlots(null);
      setIsLocked(true);
    } finally {
      setIsReverting(false);
    }
  }

  const isBusy = isSubmitting || isReverting;

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col gap-1">
        {submittedAt && (
          <p className="text-sm text-foreground/60">
            提出日時: {formatDateTime(submittedAt)}
          </p>
        )}
        {!isEditable && (
          <p className="text-sm text-red-600 dark:text-red-400">
            ※ 現在は募集期間外です。内容の変更・提出はできません。
          </p>
        )}
      </div>

      {errorMessage && (
        <p className="rounded-lg border border-black/[.08] p-4 text-sm dark:border-white/[.145]">
          {errorMessage}
        </p>
      )}
      {submittedMessage && !errorMessage && (
        <p className="rounded-lg border border-black/[.08] p-4 text-sm text-foreground/60 dark:border-white/[.145]">
          {submittedMessage}
        </p>
      )}

      {isLocked ? (
        <>
          <div className="flex flex-col gap-4">
            {slots
              .map((slot, index) => ({ slot, index }))
              .filter(({ slot }) => slot.seminarId !== "")
              .map(({ slot, index }) => {
                const seminarName =
                  seminars.find((s) => s.id === slot.seminarId)?.name ??
                  "(削除されたゼミ)";
                return (
                  <section
                    key={PRIORITY_LABELS[index]}
                    className="rounded-lg border border-black/[.08] p-4 dark:border-white/[.145]"
                  >
                    <p className="text-sm text-foreground/60">
                      {PRIORITY_LABELS[index]}
                    </p>
                    <p className="mt-1 font-semibold">{seminarName}</p>
                    <p className="mt-2 whitespace-pre-wrap text-sm">
                      {slot.reason}
                    </p>
                  </section>
                );
              })}
          </div>

          {isEditable && (
            <div className="flex flex-col gap-2 sm:flex-row">
              <button
                type="button"
                onClick={handleEditClick}
                className="rounded-full border border-black/[.08] px-4 py-2 text-sm font-medium hover:bg-black/[.04] dark:border-white/[.145] dark:hover:bg-white/[.08]"
              >
                編集する
              </button>
            </div>
          )}
        </>
      ) : (
        <>
          {slots.map((slot, index) => {
            const excludedIds = selectedSeminarIdsExcept(index);
            const options = seminars.filter(
              (seminar) =>
                !excludedIds.has(seminar.id) || seminar.id === slot.seminarId,
            );

            const seminarSelectId = `seminar-select-${index}`;
            const reasonInputId = `reason-input-${index}`;

            return (
              <section
                key={PRIORITY_LABELS[index]}
                className="rounded-lg border border-black/[.08] p-4 dark:border-white/[.145]"
              >
                <label
                  htmlFor={seminarSelectId}
                  className="block text-sm font-semibold"
                >
                  {PRIORITY_LABELS[index]}
                </label>

                <select
                  id={seminarSelectId}
                  value={slot.seminarId}
                  onChange={(e) =>
                    updateSlot(index, { seminarId: e.target.value })
                  }
                  disabled={isBusy}
                  className="mt-2 w-full rounded-lg border border-black/[.08] bg-background px-3 py-2 text-sm dark:border-white/[.145]"
                >
                  <option value="">選択してください</option>
                  {options.map((seminar) => (
                    <option key={seminar.id} value={seminar.id}>
                      {seminar.name}
                    </option>
                  ))}
                </select>

                <div className="mt-3">
                  <div className="flex items-center justify-between">
                    <label
                      htmlFor={reasonInputId}
                      className="text-sm text-foreground/60"
                    >
                      志望理由
                    </label>
                    <span className="text-xs text-foreground/40">
                      {slot.reason.length}文字
                    </span>
                  </div>
                  <textarea
                    id={reasonInputId}
                    value={slot.reason}
                    onChange={(e) =>
                      updateSlot(index, { reason: e.target.value })
                    }
                    disabled={isBusy}
                    rows={4}
                    placeholder="このゼミを志望する理由を入力してください"
                    className="mt-1 w-full rounded-lg border border-black/[.08] bg-background px-3 py-2 text-sm dark:border-white/[.145]"
                  />
                </div>
              </section>
            );
          })}

          <div className="flex flex-col gap-2 sm:flex-row">
            <button
              type="button"
              onClick={handleSubmitClick}
              disabled={isBusy}
              className="rounded-full bg-foreground px-4 py-2 text-sm font-medium text-background hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {isSubmitting ? "提出中..." : "提出する"}
            </button>
            {snapshotSlots && (
              <button
                type="button"
                onClick={handleRevertClick}
                disabled={isBusy}
                className="rounded-full border border-black/[.08] px-4 py-2 text-sm font-medium hover:bg-black/[.04] disabled:cursor-not-allowed disabled:opacity-50 dark:border-white/[.145] dark:hover:bg-white/[.08]"
              >
                {isReverting ? "戻しています..." : "戻る"}
              </button>
            )}
          </div>
        </>
      )}
    </div>
  );
}
