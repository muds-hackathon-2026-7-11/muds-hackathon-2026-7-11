"use client";

import { useSession } from "next-auth/react";
import { useState } from "react";
import { apiFetch } from "@/lib/api-client";

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
  const [status, setStatus] = useState(initialApplication.status);
  const [submittedAt, setSubmittedAt] = useState(
    initialApplication.submitted_at,
  );
  const [isEditable] = useState(initialApplication.is_editable);
  const [isSaving, setIsSaving] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [savedMessage, setSavedMessage] = useState<string | null>(null);

  if (!isEditable) {
    const filledChoices = initialApplication.choices
      .slice()
      .sort((a, b) => a.priority - b.priority);
    return (
      <section className="rounded-lg border border-black/[.08] p-6 dark:border-white/[.145]">
        <div className="flex items-center justify-between">
          <p className="font-semibold">
            {status === "submitted" ? "提出済み" : "下書き"}
          </p>
          {submittedAt && (
            <p className="text-sm text-foreground/60">
              提出日時: {formatDateTime(submittedAt)}
            </p>
          )}
        </div>
        <p className="mt-2 text-sm text-foreground/60">
          現在は提出期間外のため、閲覧のみ可能です。
        </p>

        {filledChoices.length === 0 ? (
          <p className="mt-4 text-foreground/60">提出物はありません。</p>
        ) : (
          <div className="mt-4 flex flex-col gap-4">
            {filledChoices.map((choice) => {
              const seminarName =
                seminars.find((s) => s.id === choice.seminar_id)?.name ??
                "(削除されたゼミ)";
              return (
                <div
                  key={choice.priority}
                  className="rounded-lg border border-black/[.08] p-4 dark:border-white/[.145]"
                >
                  <p className="text-sm text-foreground/60">
                    {PRIORITY_LABELS[choice.priority - 1] ??
                      `第${choice.priority}志望`}
                  </p>
                  <p className="mt-1 font-semibold">{seminarName}</p>
                  <p className="mt-2 whitespace-pre-wrap text-sm">
                    {choice.reason}
                  </p>
                </div>
              );
            })}
          </div>
        )}
      </section>
    );
  }

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

  async function extractErrorDetail(res: Response): Promise<string> {
    try {
      const body = (await res.json()) as { detail?: string };
      return body.detail ?? "エラーが発生しました。";
    } catch {
      return "エラーが発生しました。";
    }
  }

  async function saveDraft(): Promise<boolean> {
    setErrorMessage(null);
    setSavedMessage(null);

    const missing = missingReasonLabels();
    if (missing.length > 0) {
      setErrorMessage(`${missing.join("・")}の志望理由が未入力です。`);
      return false;
    }

    setIsSaving(true);
    try {
      const res = await apiFetch("/applications/me", session, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ choices: buildPayloadChoices() }),
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
    } finally {
      setIsSaving(false);
    }
  }

  async function handleSaveClick(): Promise<void> {
    const ok = await saveDraft();
    if (ok) {
      setSavedMessage("下書きを保存しました。");
    }
  }

  async function handleSubmitClick(): Promise<void> {
    if (buildPayloadChoices().length === 0) {
      setErrorMessage("志望を1件以上入力してください。");
      return;
    }

    setIsSubmitting(true);
    try {
      const saved = await saveDraft();
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
      setSavedMessage("志望を提出しました。");
    } catch {
      setErrorMessage("通信に失敗しました。時間をおいて再度お試しください。");
    } finally {
      setIsSubmitting(false);
    }
  }

  const isBusy = isSaving || isSubmitting;

  return (
    <div className="flex flex-col gap-4">
      <section className="rounded-lg border border-black/[.08] p-4 dark:border-white/[.145]">
        <div className="flex items-center justify-between">
          <p className="font-semibold">
            状態: {status === "submitted" ? "提出済み" : "下書き"}
          </p>
          {submittedAt && (
            <p className="text-sm text-foreground/60">
              提出日時: {formatDateTime(submittedAt)}
            </p>
          )}
        </div>
        {status === "submitted" && (
          <p className="mt-2 text-sm text-foreground/60">
            締切前であれば、内容を編集して再提出できます。
          </p>
        )}
      </section>

      {errorMessage && (
        <p className="rounded-lg border border-black/[.08] p-4 text-sm dark:border-white/[.145]">
          {errorMessage}
        </p>
      )}
      {savedMessage && !errorMessage && (
        <p className="rounded-lg border border-black/[.08] p-4 text-sm text-foreground/60 dark:border-white/[.145]">
          {savedMessage}
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
          onClick={handleSaveClick}
          disabled={isBusy}
          className="rounded-full border border-black/[.08] px-4 py-2 text-sm font-medium hover:bg-black/[.04] disabled:cursor-not-allowed disabled:opacity-50 dark:border-white/[.145] dark:hover:bg-white/[.08]"
        >
          {isSaving ? "保存中..." : "下書き保存"}
        </button>
        <button
          type="button"
          onClick={handleSubmitClick}
          disabled={isBusy}
          className="rounded-full bg-foreground px-4 py-2 text-sm font-medium text-background hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {isSubmitting ? "提出中..." : "提出する"}
        </button>
      </div>
    </div>
  );
}
