"use client";

import { useMemo, useState } from "react";

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
  questions: Question[];
};

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("ja-JP", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  });
}

export function FaqList({ questions }: FaqListProps) {
  const [keyword, setKeyword] = useState("");

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

  return (
    <div className="flex flex-col gap-4">
      <input
        type="text"
        value={keyword}
        onChange={(e) => setKeyword(e.target.value)}
        placeholder="質問を検索"
        className="w-full rounded-lg border border-black/[.08] bg-background px-3 py-2 text-sm dark:border-white/[.145]"
      />

      {questions.length === 0 ? (
        <p className="text-sm text-foreground/60">
          まだ質問が投稿されていません。
        </p>
      ) : filtered.length === 0 ? (
        <p className="text-sm text-foreground/60">
          該当する質問が見つかりませんでした。
        </p>
      ) : (
        <div className="flex flex-col gap-4">
          {filtered.map((question) => (
            <section
              key={question.id}
              className="rounded-lg border border-black/[.08] p-4 dark:border-white/[.145]"
            >
              <p className="whitespace-pre-wrap font-medium">
                {question.content}
              </p>
              <p className="mt-1 text-xs text-foreground/60">
                {formatDate(question.created_at)}
              </p>

              {question.answers.length === 0 ? (
                <p className="mt-3 text-sm text-foreground/60">
                  まだ回答がありません。
                </p>
              ) : (
                <div className="mt-3 flex flex-col gap-3 border-t border-black/[.08] pt-3 dark:border-white/[.145]">
                  {question.answers.map((answer) => (
                    <div key={answer.id}>
                      <p className="whitespace-pre-wrap text-sm text-foreground/80">
                        {answer.content}
                      </p>
                      <p className="mt-1 text-xs text-foreground/60">
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
