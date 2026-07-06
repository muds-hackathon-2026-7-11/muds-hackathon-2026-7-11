"use client";

import { useSession } from "next-auth/react";
import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api-client";

export type ResearchTag = {
  id: string;
  name: string;
  category: string;
};

function groupTagsByCategory(tags: ResearchTag[]): [string, ResearchTag[]][] {
  const groups = new Map<string, ResearchTag[]>();
  for (const tag of tags) {
    const group = groups.get(tag.category);
    if (group) {
      group.push(tag);
    } else {
      groups.set(tag.category, [tag]);
    }
  }
  return Array.from(groups.entries());
}

type ProfileCardProps = {
  name: string;
  email: string;
  grade: string | null;
  researchTheme: string | null;
  interestTags?: ResearchTag[];
  allTags?: ResearchTag[];
};

async function extractErrorDetail(res: Response): Promise<string> {
  const fallback = "保存に失敗しました。";
  try {
    const body = (await res.json()) as { detail?: unknown };
    // FastAPIのバリデーションエラー(422)はdetailが配列で返るため、
    // string以外はそのまま描画せずフォールバックにする。
    return typeof body.detail === "string" ? body.detail : fallback;
  } catch {
    return fallback;
  }
}

export function ProfileCard({
  name,
  email,
  grade,
  researchTheme,
  interestTags = [],
  allTags = [],
}: ProfileCardProps) {
  const { data: session } = useSession();
  const [isEditing, setIsEditing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [theme, setTheme] = useState(researchTheme ?? "");
  const [tagIds, setTagIds] = useState<Set<string>>(
    () => new Set(interestTags.map((tag) => tag.id)),
  );
  const [savedTheme, setSavedTheme] = useState(researchTheme);
  const [savedTagIds, setSavedTagIds] = useState<Set<string>>(
    () => new Set(interestTags.map((tag) => tag.id)),
  );

  function handleEditClick(): void {
    setTheme(savedTheme ?? "");
    setTagIds(new Set(savedTagIds));
    setErrorMessage(null);
    setIsEditing(true);
  }

  function handleCancelClick(): void {
    setIsEditing(false);
    setErrorMessage(null);
  }

  function toggleTag(tagId: string): void {
    setTagIds((prev) => {
      const next = new Set(prev);
      if (next.has(tagId)) {
        next.delete(tagId);
      } else {
        next.add(tagId);
      }
      return next;
    });
  }

  async function handleSaveClick(): Promise<void> {
    setIsSaving(true);
    setErrorMessage(null);
    try {
      const res = await apiFetch("/me", session, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          research_theme: theme.trim() === "" ? null : theme,
          interest_tag_ids: Array.from(tagIds),
        }),
      });
      if (!res.ok) {
        setErrorMessage(await extractErrorDetail(res));
        return;
      }
      const data = (await res.json()) as {
        research_theme: string | null;
        interest_tags: ResearchTag[];
      };
      setSavedTheme(data.research_theme);
      setSavedTagIds(new Set(data.interest_tags.map((tag) => tag.id)));
      setIsEditing(false);
    } catch {
      setErrorMessage("通信に失敗しました。時間をおいて再度お試しください。");
    } finally {
      setIsSaving(false);
    }
  }

  useEffect(() => {
    if (!isEditing) {
      return;
    }

    document.body.style.overflow = "hidden";
    function handleKeyDown(e: KeyboardEvent): void {
      if (e.key === "Escape" && !isSaving) {
        setIsEditing(false);
        setErrorMessage(null);
      }
    }
    document.addEventListener("keydown", handleKeyDown);

    return () => {
      document.body.style.overflow = "";
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [isEditing, isSaving]);

  function handleBackdropClick(e: React.MouseEvent<HTMLDivElement>): void {
    if (e.target === e.currentTarget && !isSaving) {
      handleCancelClick();
    }
  }

  const displayedTags = allTags.filter((tag) => savedTagIds.has(tag.id));

  return (
    <section className="rounded-lg border border-black/[.08] p-6 dark:border-white/[.145]">
      <div className="border-b border-black/[.08] pb-4 dark:border-white/[.145]">
        <p className="font-semibold">{name}</p>
        <p className="text-sm text-foreground/60">{email}</p>
        <p className="text-sm text-foreground/60">{grade ?? "未設定"}</p>
      </div>

      <div className="pt-4">
        <p className="text-sm text-foreground/60">研究概要</p>
        <p className="mt-1 whitespace-pre-wrap">{savedTheme ?? "未設定"}</p>

        {displayedTags.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-2">
            {displayedTags.map((tag) => (
              <span
                key={tag.id}
                className="rounded-full border border-black/[.08] px-3 py-1 text-xs text-foreground/70 dark:border-white/[.145]"
              >
                {tag.name}
              </span>
            ))}
          </div>
        )}

        <button
          type="button"
          onClick={handleEditClick}
          className="mt-4 rounded-full border border-black/[.08] px-4 py-2 text-sm font-medium hover:bg-black/[.04] dark:border-white/[.145] dark:hover:bg-white/[.08]"
        >
          編集
        </button>
      </div>

      {isEditing && (
        // biome-ignore lint/a11y/noStaticElementInteractions: 背景クリックで閉じるための領域(キーボードはEscで代替)
        // biome-ignore lint/a11y/useKeyWithClickEvents: 同上、Escキーは上のuseEffectで別途処理している
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
          onClick={handleBackdropClick}
        >
          <div
            role="dialog"
            aria-modal="true"
            aria-label="プロフィールを編集"
            className="flex max-h-[92vh] w-full max-w-6xl flex-col rounded-lg bg-background p-6 shadow-lg"
          >
            <p className="font-semibold">プロフィールを編集</p>

            {errorMessage && (
              <p className="mt-4 rounded-lg border border-black/[.08] p-3 text-sm dark:border-white/[.145]">
                {errorMessage}
              </p>
            )}

            <div className="mt-4 grid min-h-0 flex-1 grid-cols-1 gap-6 sm:grid-cols-[3fr_2fr]">
              <div className="flex min-h-0 flex-col">
                <label
                  htmlFor="research-theme-input"
                  className="text-sm text-foreground/60"
                >
                  研究概要
                </label>
                <textarea
                  id="research-theme-input"
                  value={theme}
                  onChange={(e) => setTheme(e.target.value)}
                  disabled={isSaving}
                  placeholder="研究概要を入力してください"
                  className="mt-1 min-h-64 w-full flex-1 rounded-lg border border-black/[.08] bg-background px-3 py-2 text-sm dark:border-white/[.145]"
                />
              </div>

              <div className="flex min-h-0 flex-col">
                <p className="text-sm text-foreground/60">タグ</p>
                <div className="mt-1 flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto rounded-lg border border-black/[.08] bg-black/[.02] p-3 dark:border-white/[.145] dark:bg-white/[.03]">
                  {groupTagsByCategory(allTags).map(([category, tags]) => (
                    <div key={category}>
                      <p className="text-xs font-medium text-foreground/50">
                        {category}
                      </p>
                      <div className="mt-1 flex flex-wrap gap-2">
                        {tags.map((tag) => {
                          const checked = tagIds.has(tag.id);
                          return (
                            <label
                              key={tag.id}
                              className={[
                                "cursor-pointer rounded-full border px-3 py-1 text-sm",
                                checked
                                  ? "border-foreground bg-foreground text-background"
                                  : "border-black/[.08] bg-background dark:border-white/[.145]",
                              ].join(" ")}
                            >
                              <input
                                type="checkbox"
                                checked={checked}
                                onChange={() => toggleTag(tag.id)}
                                disabled={isSaving}
                                className="sr-only"
                              />
                              {tag.name}
                            </label>
                          );
                        })}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <div className="mt-6 flex gap-2">
              <button
                type="button"
                onClick={handleSaveClick}
                disabled={isSaving}
                className="rounded-full bg-foreground px-4 py-2 text-sm font-medium text-background hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {isSaving ? "保存中..." : "保存"}
              </button>
              <button
                type="button"
                onClick={handleCancelClick}
                disabled={isSaving}
                className="rounded-full border border-black/[.08] px-4 py-2 text-sm font-medium hover:bg-black/[.04] disabled:cursor-not-allowed disabled:opacity-50 dark:border-white/[.145] dark:hover:bg-white/[.08]"
              >
                キャンセル
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
