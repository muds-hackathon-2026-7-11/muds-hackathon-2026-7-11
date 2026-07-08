"use client";

import { useSession } from "next-auth/react";
import { useState } from "react";
import { apiFetch } from "@/lib/api-client";

export type AdminTeacher = {
  id: string;
  name: string;
  email: string;
  research_title: string | null;
  research_theme: string | null;
  photo_url: string | null;
  is_active: boolean;
};

async function extractErrorDetail(res: Response): Promise<string> {
  try {
    const body = (await res.json()) as { detail?: string };
    return body.detail ?? "エラーが発生しました。";
  } catch {
    return "エラーが発生しました。";
  }
}

type AdminTeachersViewProps = {
  initialTeachers: AdminTeacher[];
};

export function AdminTeachersView({ initialTeachers }: AdminTeachersViewProps) {
  const { data: session } = useSession();
  const [teachers, setTeachers] = useState(initialTeachers);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const [editingId, setEditingId] = useState<string | null>(null);
  const [editName, setEditName] = useState("");
  const [editResearchTitle, setEditResearchTitle] = useState("");
  const [editResearchTheme, setEditResearchTheme] = useState("");
  const [editIsActive, setEditIsActive] = useState(true);
  const [isSaving, setIsSaving] = useState(false);

  function startEdit(teacher: AdminTeacher): void {
    setEditingId(teacher.id);
    setEditName(teacher.name);
    setEditResearchTitle(teacher.research_title ?? "");
    setEditResearchTheme(teacher.research_theme ?? "");
    setEditIsActive(teacher.is_active);
    setErrorMessage(null);
  }

  function cancelEdit(): void {
    setEditingId(null);
  }

  async function handleSave(teacherId: string): Promise<void> {
    setErrorMessage(null);
    if (editName.trim() === "") {
      setErrorMessage("名前を入力してください。");
      return;
    }
    setIsSaving(true);
    try {
      const res = await apiFetch(`/admin/teachers/${teacherId}`, session, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: editName,
          research_title: editResearchTitle === "" ? null : editResearchTitle,
          research_theme: editResearchTheme === "" ? null : editResearchTheme,
          is_active: editIsActive,
        }),
      });
      if (!res.ok) {
        setErrorMessage(await extractErrorDetail(res));
        return;
      }
      const updated = (await res.json()) as AdminTeacher;
      setTeachers((prev) =>
        prev.map((t) => (t.id === teacherId ? updated : t)),
      );
      setEditingId(null);
    } catch {
      setErrorMessage("通信に失敗しました。時間をおいて再度お試しください。");
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      {errorMessage && (
        <p className="rounded-2xl border-2 border-red-300 bg-white p-4 text-sm text-red-600 shadow-sm">
          {errorMessage}
        </p>
      )}

      <div className="flex flex-col gap-4">
        {teachers.map((teacher) => {
          const isEditing = editingId === teacher.id;
          return (
            <section
              key={teacher.id}
              className="rounded-2xl border-2 border-[#add8e6] bg-white p-6 shadow-sm shadow-[#add8e6]/30"
            >
              {isEditing ? (
                <div className="flex flex-col gap-2">
                  <input
                    type="text"
                    value={editName}
                    onChange={(e) => setEditName(e.target.value)}
                    className="w-full rounded-lg border border-[#add8e6]/60 bg-white px-3 py-2 text-sm text-zinc-800 focus:border-[#add8e6] focus:outline-none focus-visible:ring-2 focus-visible:ring-[#add8e6]/50"
                  />
                  <input
                    type="text"
                    value={editResearchTitle}
                    onChange={(e) => setEditResearchTitle(e.target.value)}
                    placeholder="研究タイトル"
                    maxLength={200}
                    className="w-full rounded-lg border border-[#add8e6]/60 bg-white px-3 py-2 text-sm text-zinc-800 focus:border-[#add8e6] focus:outline-none focus-visible:ring-2 focus-visible:ring-[#add8e6]/50"
                  />
                  <textarea
                    value={editResearchTheme}
                    onChange={(e) => setEditResearchTheme(e.target.value)}
                    placeholder="研究テーマ"
                    rows={2}
                    className="w-full rounded-lg border border-[#add8e6]/60 bg-white px-3 py-2 text-sm text-zinc-800 focus:border-[#add8e6] focus:outline-none focus-visible:ring-2 focus-visible:ring-[#add8e6]/50"
                  />
                  <label className="flex items-center gap-1.5 text-sm">
                    <input
                      type="checkbox"
                      checked={editIsActive}
                      onChange={(e) => setEditIsActive(e.target.checked)}
                    />
                    有効(is_active)
                  </label>
                  {!editIsActive && (
                    <p className="text-xs text-zinc-400">
                      無効にすると、この教員はログインできなくなります。
                    </p>
                  )}
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={() => handleSave(teacher.id)}
                      disabled={isSaving}
                      className="rounded-full bg-[#add8e6] px-4 py-2 text-sm font-semibold text-sky-950 shadow-sm transition-all hover:bg-[#9bcfe0] hover:shadow active:translate-y-px disabled:cursor-not-allowed disabled:opacity-50 focus:outline-none focus-visible:ring-4 focus-visible:ring-[#add8e6]/50"
                    >
                      {isSaving ? "保存中..." : "保存する"}
                    </button>
                    <button
                      type="button"
                      onClick={cancelEdit}
                      disabled={isSaving}
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
                      {teacher.name}
                      {!teacher.is_active && (
                        <span className="ml-2 text-xs font-normal text-zinc-400">
                          (無効)
                        </span>
                      )}
                    </p>
                    <p className="text-sm text-zinc-500">{teacher.email}</p>
                    <p className="mt-1 text-sm font-medium text-zinc-700">
                      {teacher.research_title ?? "研究タイトルは未設定です。"}
                    </p>
                    <p className="mt-1 whitespace-pre-wrap text-sm text-zinc-600">
                      {teacher.research_theme ?? "研究テーマは未設定です。"}
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => startEdit(teacher)}
                    className="shrink-0 rounded-full border border-[#add8e6]/60 px-3 py-1.5 text-xs font-medium text-zinc-700 transition-colors hover:bg-[#add8e6]/10"
                  >
                    編集
                  </button>
                </div>
              )}
            </section>
          );
        })}
      </div>
    </div>
  );
}
