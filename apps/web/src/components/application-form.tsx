"use client";

import { useSession } from "next-auth/react";
import { useCallback, useEffect, useRef, useState } from "react";
import { apiFetch } from "@/lib/api-client";

// バックエンドは画面を開いた後に募集期間が終了した場合、保存・提出時に
// このエラーを返す(現在募集中の期間がないため)。生のエラー文言のままだと
// 何をすればいいか伝わりにくいので、ページ更新を促す文言に置き換える。
const TERM_CLOSED_DETAIL = "現在募集中の期間がありません。";
const TERM_CLOSED_MESSAGE = "締切が過ぎました。ページを更新してください。";

const REASON_MAX_LENGTH = 400;
// 入力が止まってから自動保存するまでの待ち時間。
const AUTOSAVE_DELAY_MS = 1000;

// ゼミ未選択("選択してください")のスロットはAPIへ保存できない
// (ApplicationChoiceInはseminar_idが必須のため)。そのスロットの書きかけの
// 志望理由は、ゼミが選ばれるまでの間ブラウザのlocalStorageにだけ一時保存し、
// ページを再読み込みしても消えないようにする。
const LOCAL_DRAFT_KEY = "application-form-local-draft";

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

// エラー表示は画面上部、提出・戻るボタンは一番下にあるため、それらのボタンを
// 押した結果のエラーがボタン付近からは見えない。ユーザーが明示的に押した
// 操作の結果としてエラーが出た時だけ呼ぶこと(自動保存の失敗はユーザー操作の
// 直後ではなく、下の方で入力中に静かに走るため、ここで呼ぶと入力中の画面を
// 強制的にスクロールさせてしまう。自動保存の失敗は既存のautosaveState
// インジケータで十分)。
function scrollToTop(): void {
  window.scrollTo({ top: 0, behavior: "smooth" });
}

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

// 志望理由ごとのマッチ度診断(#119, POST /seminars/reason-matches)の応答。
type ReasonMatchRecommendation = {
  seminar_id: string;
  seminar_name: string;
  score: number;
};

type ReasonMatchResult = {
  seminar_id: string;
  seminar_name: string;
  selected_score: number | null;
  rubric: Record<string, number>;
  summary: string;
  recommendations: ReasonMatchRecommendation[];
};

type ReasonMatchesResponse = {
  results: ReasonMatchResult[];
  message: string | null;
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
    // サーバー(コンテナ)とブラウザでデフォルトタイムゾーンが異なると
    // SSRとハイドレーション時で表示がずれるため、明示的に固定する。
    timeZone: "Asia/Tokyo",
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
    const base = toSlots(initialApplication.choices);
    const localDraft = loadLocalDraft();
    if (!localDraft) {
      return base;
    }
    // サーバー側で既にゼミが選択されているスロットはサーバー側を優先し、
    // ゼミ未選択のスロットだけローカル下書きで補う。
    return base.map((slot, index) =>
      slot.seminarId === "" ? localDraft[index] : slot,
    ) as [Slot, Slot, Slot];
  });
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
  // 編集中に自動保存が一度でも成功すると、サーバー側は「編集する」を
  // 押した時点のスナップショットとは食い違った状態になる。このrefは
  // その状態だけを追跡し、「戻る」を押した時に本当に必要な場合だけ
  // サーバーへスナップショットを書き戻す(毎回PUTすると提出日時が
  // 更新されたりマッチ度が消えたりするため、不要な時は絶対に呼ばない)。
  const serverDirtySinceEdit = useRef(false);
  const [autosaveState, setAutosaveState] = useState<
    "idle" | "saving" | "saved" | "error"
  >("idle");
  // マウント直後(まだ何も編集していない状態)に自動保存が走らないようにする
  // ためのガード。
  const isFirstRender = useRef(true);
  // persistChoicesの呼び出し(自動保存・提出・戻る)を直列化するキュー。
  // ネットワークが遅い状態で入力を続けると自動保存同士が、あるいは
  // 自動保存の途中で「提出する」を押すと自動保存と提出が、それぞれ
  // 並行にPUTを送ってしまい、後から解決した方が新しい入力を古い内容で
  // 上書きしかねない。呼び出しを1本のPromiseチェーンに繋ぎ、常に前の
  // PUTが完了してから次のPUTを送るようにする。
  const persistQueue = useRef<Promise<void>>(Promise.resolve());

  // 志望理由ごとのマッチ度診断結果。キーは選んだゼミのseminar_id。
  const [matchBySeminarId, setMatchBySeminarId] = useState<
    Record<string, ReasonMatchResult>
  >({});
  const [isDiagnosing, setIsDiagnosing] = useState(false);
  const [matchMessage, setMatchMessage] = useState<string | null>(null);

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
    // 内容が変わったら古い診断結果は無効。表示を消す。
    setMatchBySeminarId({});
    setMatchMessage(null);
  }

  // 志望理由ごとのマッチ度診断。targetIndex を渡すとその志望だけ採点する
  // (未指定なら理由が入っている全志望)。第1〜3志望のゼミは常に「他ゼミTop3」
  // から除外するため、採点対象でなくても選択済みゼミは全てリクエストに含める。
  async function handleMatchDiagnose(targetIndex?: number): Promise<void> {
    setMatchMessage(null);
    const filled = slots
      .map((slot, index) => ({ slot, index }))
      .filter(({ slot }) => slot.seminarId !== "");
    const targetIdx = new Set(
      filled
        .filter(
          ({ slot, index }) =>
            slot.reason.trim() !== "" &&
            (targetIndex === undefined || index === targetIndex),
        )
        .map(({ index }) => index),
    );
    if (targetIdx.size === 0) {
      setMatchMessage("ゼミと志望理由を入力してから診断してください。");
      return;
    }

    const choices = filled.map(({ slot, index }) => ({
      seminar_id: slot.seminarId,
      // 採点対象の志望だけ理由を送る。他は除外目的でゼミIDのみ。
      reason: targetIdx.has(index) ? slot.reason : "",
    }));

    setIsDiagnosing(true);
    try {
      const res = await apiFetch("/seminars/reason-matches", session, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ choices }),
      });
      if (!res.ok) {
        throw new Error(`reason-matches failed: ${res.status}`);
      }
      const data = (await res.json()) as ReasonMatchesResponse;
      setMatchBySeminarId((prev) => {
        const next = { ...prev };
        for (const result of data.results) {
          next[result.seminar_id] = result;
        }
        return next;
      });
      if (data.results.length === 0 && data.message) {
        setMatchMessage(data.message);
      }
    } catch {
      setMatchMessage("診断に失敗しました。時間をおいて再度お試しください。");
    } finally {
      setIsDiagnosing(false);
    }
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
  // 呼び出し元は「提出する」、提出失敗後の「戻る」(サーバー側が編集後の
  // 内容のまま残っている場合のみ)、そして自動保存の3箇所。保存対象を
  // 引数で明示的に受け取るのは、「戻る」の時は現在のslots stateではなく
  // スナップショットを送りたいため。
  //
  // 注意: バックエンドのPUTは、既に提出済み(status=submitted)のフォームに
  // 対しては内容が変わっていなくても提出日時(submitted_at)を更新し、
  // match_score/match_feedbackを常にクリアする。自動保存はこの副作用を
  // 承知の上で許容する(提出済みの内容を編集し始めた時点で、いずれ
  // match_score等は再計算が必要になるため)。
  const persistChoices = useCallback(
    (slotsToSave: [Slot, Slot, Slot]): Promise<boolean> => {
      const run = async (): Promise<boolean> => {
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
          // ゼミ未選択("選択してください")のスロットはリクエストから除外して
          // おり、サーバーの応答にも含まれない。そのスロットまで応答で
          // 上書きすると、ゼミ未選択のまま書きかけの志望理由が消えてしまう
          // ため、送っていないスロットは現在のローカル状態をそのまま残す。
          const saved = toSlots(data.choices);
          setSlots(
            (prev) =>
              prev.map((slot, index) =>
                slotsToSave[index].seminarId === "" ? slot : saved[index],
              ) as [Slot, Slot, Slot],
          );
          return true;
        } catch {
          setErrorMessage(
            "通信に失敗しました。時間をおいて再度お試しください。",
          );
          return false;
        }
      };

      // 前のPUT(自動保存・提出・戻るのいずれか)が完了してから実行する。
      // 前の呼び出しが失敗していてもチェーン自体は止めない。
      const result = persistQueue.current.then(run);
      persistQueue.current = result.then(
        () => undefined,
        () => undefined,
      );
      return result;
    },
    [session],
  );

  // 「編集する」で入力可能になっている間、入力が止まって
  // AUTOSAVE_DELAY_MS 経過したら自動でサーバーへ保存する。
  useEffect(() => {
    if (isFirstRender.current) {
      isFirstRender.current = false;
      return;
    }
    if (isLocked || isSubmitting || isReverting) {
      return;
    }

    const timer = setTimeout(async () => {
      // ゼミ未選択のままの志望理由はAPIへ保存できないため、
      // localStorageへの一時保存/クリアだけ行う。
      const hasOrphanReason = slots.some(
        (slot) => slot.seminarId === "" && slot.reason.trim() !== "",
      );
      if (hasOrphanReason) {
        saveLocalDraft(slots);
      } else {
        clearLocalDraft();
      }

      const hasSelectedSeminar = slots.some((slot) => slot.seminarId !== "");
      if (!hasSelectedSeminar) {
        return;
      }

      setAutosaveState("saving");
      const ok = await persistChoices(slots);
      if (ok) {
        serverDirtySinceEdit.current = true;
        setAutosaveState("saved");
      } else {
        setAutosaveState("error");
      }
    }, AUTOSAVE_DELAY_MS);

    return () => clearTimeout(timer);
  }, [slots, isLocked, isSubmitting, isReverting, persistChoices]);

  async function handleSubmitClick(): Promise<void> {
    setErrorMessage(null);
    setSubmittedMessage(null);

    if (buildPayloadChoices().length === 0) {
      setErrorMessage("志望を1件以上入力してください。");
      scrollToTop();
      return;
    }
    const missing = missingReasonLabels();
    if (missing.length > 0) {
      setErrorMessage(`${missing.join("・")}の志望理由が未入力です。`);
      scrollToTop();
      return;
    }

    setIsSubmitting(true);
    try {
      const saved = await persistChoices(slots);
      if (!saved) {
        scrollToTop();
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
        scrollToTop();
        return;
      }
      const data = (await res.json()) as ApplicationFormData;
      setSubmittedAt(data.submitted_at);
      setSlots(toSlots(data.choices));
      setSubmittedMessage("提出が完了しました。");
      setIsLocked(true);
      setSnapshotSlots(null);
      serverDirtySinceEdit.current = false;
    } catch {
      setErrorMessage("通信に失敗しました。時間をおいて再度お試しください。");
      scrollToTop();
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
  // ローカル下書き(localStorage)を、渡されたスロットの内容に合わせ直す。
  // 「戻る」で編集中の内容を捨てる際、編集中に書きかけていた
  // ゼミ未選択分の下書きも一緒に捨てる(スナップショット自身に
  // ゼミ未選択の下書きが含まれていれば、それはそのまま残す)。
  function resyncLocalDraft(slotsToKeep: [Slot, Slot, Slot]): void {
    const hasOrphanReason = slotsToKeep.some(
      (slot) => slot.seminarId === "" && slot.reason.trim() !== "",
    );
    if (hasOrphanReason) {
      saveLocalDraft(slotsToKeep);
    } else {
      clearLocalDraft();
    }
  }

  async function handleRevertClick(): Promise<void> {
    if (!snapshotSlots) {
      setIsLocked(true);
      return;
    }

    if (!serverDirtySinceEdit.current) {
      setSlots(snapshotSlots);
      resyncLocalDraft(snapshotSlots);
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
        scrollToTop();
        return;
      }
      resyncLocalDraft(snapshotSlots);
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
      {(submittedAt || !isEditable) && (
        <div className="flex flex-col gap-1">
          {submittedAt && (
            <p className="text-sm text-zinc-500">
              提出日時: {formatDateTime(submittedAt)}
            </p>
          )}
          {!isEditable && (
            <p className="text-sm text-red-600">
              ※ 現在は募集期間外です。内容の変更・提出はできません。
            </p>
          )}
        </div>
      )}

      {errorMessage && (
        <p className="rounded-2xl border-2 border-red-300 bg-white p-4 text-sm text-red-600 shadow-sm">
          {errorMessage}
        </p>
      )}
      {submittedMessage && !errorMessage && (
        <p className="text-xl text-zinc-700">{submittedMessage}</p>
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
                    className="rounded-2xl border-2 border-[#add8e6] bg-white p-4 shadow-sm shadow-[#add8e6]/30"
                  >
                    <p className="text-lg font-bold text-zinc-700">
                      {PRIORITY_LABELS[index]}
                    </p>
                    <p className="mt-1 text-lg font-bold text-zinc-800">
                      {seminarName}
                    </p>
                    <p className="mt-2 whitespace-pre-wrap text-sm text-zinc-700">
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
                className="rounded-full bg-[#add8e6] px-5 py-2 text-sm font-semibold text-sky-950 shadow-sm transition-all hover:bg-[#9bcfe0] hover:shadow active:translate-y-px focus:outline-none focus-visible:ring-4 focus-visible:ring-[#add8e6]/50"
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
                className="rounded-2xl border-2 border-[#add8e6] bg-white p-4 shadow-sm shadow-[#add8e6]/30"
              >
                <label
                  htmlFor={seminarSelectId}
                  className="block text-2xl font-bold text-zinc-800"
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
                  className="mt-2 w-full rounded-lg border border-[#add8e6]/60 bg-white px-3 py-2 text-sm text-zinc-800 focus:border-[#add8e6] focus:outline-none focus-visible:ring-2 focus-visible:ring-[#add8e6]/50"
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
                      className="text-sm text-zinc-500"
                    >
                      志望理由
                    </label>
                    <span className="text-xs text-zinc-400">
                      {slot.reason.length}/{REASON_MAX_LENGTH}文字
                    </span>
                  </div>
                  <textarea
                    id={reasonInputId}
                    value={slot.reason}
                    onChange={(e) =>
                      updateSlot(index, { reason: e.target.value })
                    }
                    disabled={isBusy}
                    rows={8}
                    maxLength={REASON_MAX_LENGTH}
                    placeholder="このゼミを志望する理由を入力してください"
                    className="mt-1 min-h-40 w-full resize-y rounded-lg border border-[#add8e6]/60 bg-white px-3 py-2 text-sm leading-relaxed text-zinc-800 focus:border-[#add8e6] focus:outline-none focus-visible:ring-2 focus-visible:ring-[#add8e6]/50"
                  />
                  <div className="mt-2 flex justify-end">
                    <button
                      type="button"
                      onClick={() => void handleMatchDiagnose(index)}
                      disabled={
                        isBusy ||
                        isDiagnosing ||
                        slot.seminarId === "" ||
                        slot.reason.trim() === ""
                      }
                      className="rounded-full border border-[#add8e6] bg-white px-3 py-1 text-xs font-semibold text-sky-900 hover:bg-[#add8e6]/10 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      {isDiagnosing ? "診断中..." : "◎ マッチ度診断"}
                    </button>
                  </div>
                </div>
                {slot.seminarId !== "" && matchBySeminarId[slot.seminarId] && (
                  <ReasonMatchPanel result={matchBySeminarId[slot.seminarId]} />
                )}
              </section>
            );
          })}

          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={handleSubmitClick}
              disabled={isBusy}
              className="rounded-full bg-[#add8e6] px-5 py-2 text-sm font-semibold text-sky-950 shadow-sm transition-all hover:bg-[#9bcfe0] hover:shadow active:translate-y-px disabled:cursor-not-allowed disabled:opacity-50 focus:outline-none focus-visible:ring-4 focus-visible:ring-[#add8e6]/50"
            >
              {isSubmitting ? "提出中..." : "提出する"}
            </button>
            <button
              type="button"
              onClick={() => void handleMatchDiagnose()}
              disabled={isBusy || isDiagnosing}
              className="rounded-full border border-[#add8e6] bg-white px-5 py-2 text-sm font-medium text-sky-900 hover:bg-[#add8e6]/10 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {isDiagnosing ? "診断中..." : "マッチ度診断（まとめて）"}
            </button>
            {snapshotSlots && (
              <button
                type="button"
                onClick={handleRevertClick}
                disabled={isBusy}
                className="rounded-full border border-[#e6e6e6] bg-white px-5 py-2 text-sm font-medium text-zinc-600 hover:bg-[#e6e6e6]/50 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {isReverting ? "戻しています..." : "戻る"}
              </button>
            )}
            <span className="text-xs text-foreground/40" aria-live="polite">
              {autosaveState === "saving" && "保存中..."}
              {autosaveState === "saved" && "保存済み"}
              {autosaveState === "error" && "自動保存に失敗しました"}
            </span>
          </div>
          {matchMessage && (
            <p className="text-sm text-sky-900">{matchMessage}</p>
          )}
        </>
      )}
    </div>
  );
}

const RUBRIC_LABELS: [string, string][] = [
  ["研究分野", "field"],
  ["手法・技術", "method"],
  ["興味テーマ", "interest"],
  ["育成方針", "style"],
];

// 志望理由の直下に表示する診断結果パネル。選んだゼミのマッチ度(あれば)と、
// その理由に相性の良い他ゼミTop3(第1〜3志望を除く)を表示する。
function ReasonMatchPanel({ result }: { result: ReasonMatchResult }) {
  return (
    <div className="mt-3 rounded-xl border border-[#add8e6]/60 bg-[#add8e6]/10 p-3">
      {result.selected_score !== null && (
        <div>
          <div className="flex items-end justify-between">
            <span className="text-xs font-semibold text-zinc-500">
              マッチ度（{result.seminar_name}）
            </span>
            <span className="text-2xl font-extrabold tabular-nums text-sky-900">
              {result.selected_score}
              <span className="text-sm">%</span>
            </span>
          </div>
          <div className="mt-1.5 h-2 overflow-hidden rounded-full bg-[#add8e6]/30">
            <div
              className="h-full rounded-full bg-[#add8e6]"
              style={{ width: `${result.selected_score}%` }}
            />
          </div>
          <div className="mt-2 flex flex-wrap gap-1.5">
            {RUBRIC_LABELS.map(([label, key]) => (
              <span
                key={key}
                className="rounded border border-[#add8e6]/60 bg-white/70 px-2 py-0.5 text-[11px] tabular-nums text-zinc-600"
              >
                {label}
                <b className="ml-1 text-sky-900">{result.rubric[key] ?? 0}</b>
              </span>
            ))}
          </div>
          {result.summary && (
            <p className="mt-2 text-sm text-zinc-600">{result.summary}</p>
          )}
        </div>
      )}

      {result.recommendations.length > 0 && (
        <div className="mt-3 border-t border-dashed border-[#add8e6]/60 pt-2.5">
          <p className="text-xs font-bold text-zinc-700">
            この志望理由に相性の良いゼミ{" "}
            <span className="font-medium text-zinc-500">
              （第1〜3志望を除く）
            </span>
          </p>
          <ul className="mt-1.5 flex flex-col gap-1">
            {result.recommendations.map((rec, i) => (
              <li
                key={rec.seminar_id}
                className="grid grid-cols-[18px_1fr_auto] items-center gap-2"
              >
                <span className="grid h-[18px] w-[18px] place-items-center rounded-full border border-[#add8e6]/60 bg-white text-[11px] font-bold text-sky-900">
                  {i + 1}
                </span>
                <span>
                  <span className="block text-sm font-semibold text-zinc-700">
                    {rec.seminar_name}
                  </span>
                  <span className="mt-0.5 block h-[3px] overflow-hidden rounded-full bg-[#add8e6]/30">
                    <span
                      className="block h-full rounded-full bg-[#add8e6]"
                      style={{ width: `${rec.score}%` }}
                    />
                  </span>
                </span>
                <span className="text-sm font-extrabold tabular-nums text-sky-900">
                  {rec.score}
                  <span className="text-[11px]">%</span>
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
