"use client";

import { useSession } from "next-auth/react";
import { useState } from "react";
import { apiFetch } from "@/lib/api-client";

export type AdminTeacher = {
  id: string;
  name: string;
  email: string;
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
  const [editEmail, setEditEmail] = useState("");
  const [editIsActive, setEditIsActive] = useState(true);
  const [isSaving, setIsSaving] = useState(false);

  // 削除は編集フォームとは別の即時操作として扱う。
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const [isCreateFormOpen, setIsCreateFormOpen] = useState(false);
  const [newName, setNewName] = useState("");
  const [newEmail, setNewEmail] = useState("");
  const [isCreating, setIsCreating] = useState(false);

  function openCreateForm(): void {
    setIsCreateFormOpen(true);
    setErrorMessage(null);
  }

  function cancelCreate(): void {
    setIsCreateFormOpen(false);
    setNewName("");
    setNewEmail("");
    setErrorMessage(null);
  }

  function startEdit(teacher: AdminTeacher): void {
    setEditingId(teacher.id);
    setEditName(teacher.name);
    setEditEmail(teacher.email);
    setEditIsActive(teacher.is_active);
    setErrorMessage(null);
  }

  function cancelEdit(): void {
    setEditingId(null);
  }

  async function handleSave(teacherId: string): Promise<void> {
    setErrorMessage(null);
    if (editName.trim() === "" || editEmail.trim() === "") {
      setErrorMessage("名前とメールアドレスを入力してください。");
      return;
    }
    setIsSaving(true);
    try {
      const res = await apiFetch(`/admin/teachers/${teacherId}`, session, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: editName,
          email: editEmail,
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

  async function handleDelete(teacher: AdminTeacher): Promise<void> {
    const confirmed = window.confirm(
      `「${teacher.name}」を削除します(無効化され、ログインできなくなります)。よろしいですか?`,
    );
    if (!confirmed) {
      return;
    }
    setErrorMessage(null);
    setDeletingId(teacher.id);
    try {
      const res = await apiFetch(`/admin/teachers/${teacher.id}`, session, {
        method: "DELETE",
      });
      if (!res.ok) {
        setErrorMessage(await extractErrorDetail(res));
        return;
      }
      setTeachers((prev) =>
        prev.map((t) => (t.id === teacher.id ? { ...t, is_active: false } : t)),
      );
    } catch {
      setErrorMessage("通信に失敗しました。時間をおいて再度お試しください。");
    } finally {
      setDeletingId(null);
    }
  }

  async function handleCreate(): Promise<void> {
    setErrorMessage(null);
    if (newName.trim() === "" || newEmail.trim() === "") {
      setErrorMessage("名前とメールアドレスを入力してください。");
      return;
    }
    setIsCreating(true);
    try {
      const res = await apiFetch("/admin/teachers", session, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: newName, email: newEmail }),
      });
      if (!res.ok) {
        setErrorMessage(await extractErrorDetail(res));
        return;
      }
      const created = (await res.json()) as AdminTeacher;
      setTeachers((prev) => [...prev, created]);
      setNewName("");
      setNewEmail("");
      setIsCreateFormOpen(false);
    } catch {
      setErrorMessage("通信に失敗しました。時間をおいて再度お試しください。");
    } finally {
      setIsCreating(false);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      {errorMessage && (
        <p className="rounded-2xl border-2 border-red-300 bg-white p-4 text-sm text-red-600 shadow-sm">
          {errorMessage}
        </p>
      )}

      <button
        type="button"
        onClick={openCreateForm}
        className="self-start rounded-full bg-[#add8e6] px-4 py-2 text-sm font-semibold text-sky-950 shadow-sm transition-all hover:bg-[#9bcfe0]"
      >
        + 教員を追加
      </button>

      {isCreateFormOpen && (
        // biome-ignore lint/a11y/noStaticElementInteractions: 背景クリックで閉じるための領域
        // biome-ignore lint/a11y/useKeyWithClickEvents: 閉じるはキャンセルボタンで代替する
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
          onClick={(e) => {
            if (e.target === e.currentTarget && !isCreating) {
              cancelCreate();
            }
          }}
        >
          <section
            role="dialog"
            aria-modal="true"
            aria-label="教員を追加"
            className="w-full max-w-lg rounded-2xl border border-line bg-white p-6 shadow-lg shadow-[#add8e6]/30"
          >
            <h2 className="text-lg font-bold text-zinc-900">教員を追加</h2>
            <div className="mt-4 flex flex-col gap-2">
              <input
                type="text"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                placeholder="名前"
                className="w-full rounded-lg border border-[#add8e6]/60 bg-white px-3 py-2 text-sm"
              />
              <input
                type="email"
                value={newEmail}
                onChange={(e) => setNewEmail(e.target.value)}
                placeholder="メールアドレス"
                className="w-full rounded-lg border border-[#add8e6]/60 bg-white px-3 py-2 text-sm"
              />
              <div className="mt-2 flex gap-2">
                <button
                  type="button"
                  onClick={handleCreate}
                  disabled={isCreating}
                  className="rounded-full bg-[#add8e6] px-5 py-2 text-sm font-semibold text-sky-950 shadow-sm transition-all hover:bg-[#9bcfe0] disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {isCreating ? "追加中..." : "追加する"}
                </button>
                <button
                  type="button"
                  onClick={cancelCreate}
                  disabled={isCreating}
                  className="rounded-full border border-[#e6e6e6] bg-white px-5 py-2 text-sm font-medium text-zinc-600 hover:bg-[#e6e6e6]/50 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  キャンセル
                </button>
              </div>
            </div>
          </section>
        </div>
      )}

      <div className="flex flex-col gap-4">
        {teachers.map((teacher) => {
          const isEditing = editingId === teacher.id;
          return (
            <section
              key={teacher.id}
              className="rounded-2xl border border-line bg-white p-6 shadow-sm shadow-[#add8e6]/30"
            >
              {isEditing ? (
                <div className="flex flex-col gap-2">
                  <input
                    type="text"
                    value={editName}
                    onChange={(e) => setEditName(e.target.value)}
                    placeholder="名前"
                    className="w-full rounded-lg border border-[#add8e6]/60 bg-white px-3 py-2 text-sm text-zinc-800 focus:border-[#add8e6] focus:outline-none focus-visible:ring-2 focus-visible:ring-[#add8e6]/50"
                  />
                  <input
                    type="email"
                    value={editEmail}
                    onChange={(e) => setEditEmail(e.target.value)}
                    placeholder="メールアドレス"
                    className="w-full rounded-lg border border-[#add8e6]/60 bg-white px-3 py-2 text-sm text-zinc-800 focus:border-[#add8e6] focus:outline-none focus-visible:ring-2 focus-visible:ring-[#add8e6]/50"
                  />
                  <label className="flex items-center gap-1.5 text-sm text-zinc-700">
                    <input
                      type="checkbox"
                      checked={editIsActive}
                      onChange={(e) => setEditIsActive(e.target.checked)}
                      className="h-4 w-4 accent-[#add8e6]"
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
                  </div>
                  <div className="flex shrink-0 gap-2">
                    <button
                      type="button"
                      onClick={() => startEdit(teacher)}
                      className="rounded-full border border-[#add8e6]/60 px-3 py-1.5 text-xs font-medium text-zinc-700 transition-colors hover:bg-[#add8e6]/10"
                    >
                      編集
                    </button>
                    <button
                      type="button"
                      onClick={() => handleDelete(teacher)}
                      disabled={deletingId === teacher.id || !teacher.is_active}
                      className="rounded-full border border-[#add8e6]/60 px-3 py-1.5 text-xs font-medium text-red-600 transition-colors hover:bg-[#add8e6]/10 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      {deletingId === teacher.id ? "削除中..." : "削除"}
                    </button>
                  </div>
                </div>
              )}
            </section>
          );
        })}
      </div>
    </div>
  );
}
