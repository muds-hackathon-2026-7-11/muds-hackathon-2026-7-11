"use client";

import { useSession } from "next-auth/react";
import { useMemo, useState } from "react";
import { apiFetch } from "@/lib/api-client";

export type Answer = {
  id: string;
  content: string;
  answerer_name: string;
  created_at: string;
};

export type Question = {
  id: string;
  content: string;
  status: string;
  created_at: string;
  answers: Answer[];
};

type FaqListProps = {
  seminarId: string;
  questions: Question[];
};

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("ja-JP", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    // サーバー(コンテナ)とブラウザでデフォルトタイムゾーンが異なると
    // SSRとハイドレーション時で表示がずれるため、明示的に固定する。
    timeZone: "Asia/Tokyo",
  });
}

async function extractErrorDetail(res: Response): Promise<string> {
  try {
    const body = (await res.json()) as { detail?: string };
    return body.detail ?? "エラーが発生しました。";
  } catch {
    return "エラーが発生しました。";
  }
}

export function FaqList({
  seminarId,
  questions: initialQuestions,
}: FaqListProps) {
  const { data: session } = useSession();
  const [questions, setQuestions] = useState(initialQuestions);
  const [keyword, setKeyword] = useState("");

  const [content, setContent] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const filtered = useMemo(() => {
    const trimmed = keyword.trim().toLowerCase();
    if (trimmed === "") {
      return questions;
    }
    return questions.filter(
      (q) =>
        q.content.toLowerCase().includes(trimmed) ||
        q.answers.some((a) => a.content.toLowerCase().includes(trimmed)),
    );
  }, [questions, keyword]);

  async function handleSubmit(): Promise<void> {
    setErrorMessage(null);
    if (content.trim() === "") {
      setErrorMessage("質問内容を入力してください。");
      return;
    }
    setIsSubmitting(true);
    try {
      const res = await apiFetch("/questions/me", session, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ seminar_id: seminarId, content }),
      });
      if (!res.ok) {
        setErrorMessage(await extractErrorDetail(res));
        return;
      }
      const created = (await res.json()) as Omit<Question, "answers">;
      setQuestions((prev) => [{ ...created, answers: [] }, ...prev]);
      setContent("");
    } catch {
      setErrorMessage("通信に失敗しました。時間をおいて再度お試しください。");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <section className="rounded-2xl border-2 border-[#add8e6] bg-white p-4 shadow-sm shadow-[#add8e6]/30">
        <p className="text-sm font-semibold text-zinc-800">質問する</p>
        <textarea
          value={content}
          onChange={(e) => setContent(e.target.value)}
          placeholder="ゼミへの質問を入力してください"
          rows={3}
          className="mt-2 w-full rounded-lg border border-[#add8e6]/60 bg-white px-3 py-2 text-sm text-zinc-800 focus:border-[#add8e6] focus:outline-none focus-visible:ring-2 focus-visible:ring-[#add8e6]/50"
        />
        {errorMessage && (
          <p className="mt-2 text-sm text-red-600">{errorMessage}</p>
        )}
        <button
          type="button"
          onClick={handleSubmit}
          disabled={isSubmitting}
          className="mt-3 rounded-full bg-[#add8e6] px-5 py-2 text-sm font-semibold text-sky-950 shadow-sm transition-all hover:bg-[#9bcfe0] hover:shadow active:translate-y-px disabled:cursor-not-allowed disabled:opacity-50 focus:outline-none focus-visible:ring-4 focus-visible:ring-[#add8e6]/50"
        >
          {isSubmitting ? "送信中..." : "質問を送信"}
        </button>
      </section>

      <input
        type="text"
        value={keyword}
        onChange={(e) => setKeyword(e.target.value)}
        placeholder="質問を検索"
        className="w-full rounded-lg border border-[#add8e6]/60 bg-white px-3 py-2 text-sm text-zinc-800 focus:border-[#add8e6] focus:outline-none focus-visible:ring-2 focus-visible:ring-[#add8e6]/50"
      />

      {questions.length === 0 ? (
        <p className="text-sm text-zinc-500">まだ質問が投稿されていません。</p>
      ) : filtered.length === 0 ? (
        <p className="text-sm text-zinc-500">
          該当する質問が見つかりませんでした。
        </p>
      ) : (
        <div className="flex flex-col gap-4">
          {filtered.map((question) => (
            <section
              key={question.id}
              className="rounded-2xl border-2 border-[#add8e6] bg-white p-4 shadow-sm shadow-[#add8e6]/30"
            >
              <p className="whitespace-pre-wrap font-semibold text-zinc-800">
                {question.content}
              </p>
              <p className="mt-1 text-xs text-zinc-400">
                {formatDate(question.created_at)}
              </p>

              {question.answers.length === 0 ? (
                <p className="mt-3 text-sm text-zinc-500">
                  まだ回答がありません。
                </p>
              ) : (
                <div className="mt-3 flex flex-col gap-3 border-t border-[#add8e6]/40 pt-3">
                  {question.answers.map((answer) => (
                    <div key={answer.id}>
                      <p className="whitespace-pre-wrap text-sm text-zinc-700">
                        {answer.content}
                      </p>
                      <p className="mt-1 text-xs text-zinc-400">
                        {answer.answerer_name} ・{" "}
                        {formatDate(answer.created_at)}
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </section>
          ))}
        </div>
      )}
    </div>
  );
}
