"use client";

import { useSession } from "next-auth/react";
import { useCallback, useEffect, useRef, useState } from "react";
import { apiFetch } from "@/lib/api-client";

const AUTOSAVE_DELAY_MS = 1000;
const LOCAL_DRAFT_KEY = "application-form-local-draft";

// 募集期間外(is_editable=false)はAPIへの保存自体ができない(バックエンドが
// 現在募集中の期間がない場合はPUTを拒否する)。そのため、この間の自動保存は
// ブラウザのlocalStorageへ書くだけにし、募集期間が始まったら本人が改めて
// 内容を確認・上書きしてサーバーへ保存する想定にする。
function loadLocalDraft(): [Slot, Slot, Slot] | null {
  if (typeof window === "undefined") {
    return null;
  }
  try {
    const raw = window.localStorage.getItem(LOCAL_DRAFT_KEY);
    if (!raw) {
      return null;
    }
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed) || parsed.length !== 3) {
      return null;
    }
    return parsed as [Slot, Slot, Slot];
  } catch {
    return null;
  }
}

function saveLocalDraft(slots: [Slot, Slot, Slot]): void {
  if (typeof window === "undefined") {
    return;
  }
  try {
    window.localStorage.setItem(LOCAL_DRAFT_KEY, JSON.stringify(slots));
  } catch {
    // ストレージが使えない環境(プライベートモード等)では何もしない。
  }
}

function clearLocalDraft(): void {
  if (typeof window === "undefined") {
    return;
  }
  try {
    window.localStorage.removeItem(LOCAL_DRAFT_KEY);
  } catch {
    // ストレージが使えない環境(プライベートモード等)では何もしない。
  }
}

async function extractErrorDetail(res: Response): Promise<string> {
  try {
    const body = (await res.json()) as { detail?: string };
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
  const [slots, setSlots] = useState<[Slot, Slot, Slot]>(() => {
    if (!initialApplication.is_editable) {
      return loadLocalDraft() ?? toSlots(initialApplication.choices);
    }
    return toSlots(initialApplication.choices);
  });
  const [status, setStatus] = useState(initialApplication.status);
  const [submittedAt, setSubmittedAt] = useState(
    initialApplication.submitted_at,
  );
  const isEditable = initialApplication.is_editable;
  const [autosaveState, setAutosaveState] = useState<
    "idle" | "saving" | "saved" | "error"
  >("idle");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [submittedMessage, setSubmittedMessage] = useState<string | null>(null);
  const isFirstRender = useRef(true);

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

  // 保存(PUT)本体。バリデーションはせず、今の入力内容をそのまま保存する
  // (Googleフォームのように、ボタンを押さなくても裏で保存され続ける)。
  const persistChoices = useCallback(async (): Promise<boolean> => {
    try {
      const res = await apiFetch("/applications/me", session, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          choices: slots
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
      setStatus(data.status);
      setSubmittedAt(data.submitted_at);
      setSlots(toSlots(data.choices));
      return true;
    } catch {
      setErrorMessage("通信に失敗しました。時間をおいて再度お試しください。");
      return false;
    }
  }, [session, slots]);

  // 入力が止まってから一定時間後に自動保存する(タイピング中に毎回保存
  // リクエストを送らないため)。募集期間外はAPIへは保存できないので、
  // ブラウザのlocalStorageにだけ保存する(募集期間中はAPIへ保存する)。
  useEffect(() => {
    if (isFirstRender.current) {
      isFirstRender.current = false;
      return;
    }
    if (isSubmitting) {
      return;
    }

    if (!isEditable) {
      const timer = setTimeout(() => {
        saveLocalDraft(slots);
        setAutosaveState("saved");
      }, AUTOSAVE_DELAY_MS);
      return () => clearTimeout(timer);
    }

    const timer = setTimeout(async () => {
      setAutosaveState("saving");
      setErrorMessage(null);
      const ok = await persistChoices();
      setAutosaveState(ok ? "saved" : "error");
    }, AUTOSAVE_DELAY_MS);

    return () => clearTimeout(timer);
  }, [isEditable, isSubmitting, persistChoices, slots]);

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
      const saved = await persistChoices();
      if (!saved) {
        return;
      }

      const res = await apiFetch("/applications/me/submit", session, {
        method: "POST",
      });
      if (!res.ok) {
        setErrorMessage(await extractErrorDetail(res));
        return;
      }
      const data = (await res.json()) as ApplicationFormData;
      setStatus(data.status);
      setSubmittedAt(data.submitted_at);
      setSlots(toSlots(data.choices));
      setSubmittedMessage("志望を提出しました。");
      clearLocalDraft();
    } catch {
      setErrorMessage("通信に失敗しました。時間をおいて再度お試しください。");
    } finally {
      setIsSubmitting(false);
    }
  }

  const isBusy = isSubmitting;
  const autosaveLabel = {
    idle: "",
    saving: "保存中...",
    saved: isEditable ? "保存済み" : "端末に保存済み",
    error: "",
  }[autosaveState];

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <div className="flex flex-col gap-1">
          {submittedAt && (
            <p className="text-sm text-foreground/60">
              提出日時: {formatDateTime(submittedAt)}
            </p>
          )}
          {isEditable && status === "submitted" && (
            <p className="text-sm text-foreground/60">
              締切前であれば、内容を編集して再提出できます。
            </p>
          )}
          {!isEditable && (
            <p className="text-sm text-red-600 dark:text-red-400">
              ※
              現在は募集期間外です。内容はこの端末に保存されますが、提出はできません。
            </p>
          )}
        </div>
        {autosaveLabel && (
          <p className="shrink-0 text-xs text-foreground/40">{autosaveLabel}</p>
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
              onChange={(e) => updateSlot(index, { seminarId: e.target.value })}
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
                onChange={(e) => updateSlot(index, { reason: e.target.value })}
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
          disabled={isBusy || !isEditable}
          title={isEditable ? undefined : "募集期間外のため提出できません"}
          className="rounded-full bg-foreground px-4 py-2 text-sm font-medium text-background hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {isSubmitting ? "提出中..." : "提出する"}
        </button>
      </div>
    </div>
  );
}
