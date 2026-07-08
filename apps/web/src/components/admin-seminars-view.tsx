"use client";

import Link from "next/link";
import { useSession } from "next-auth/react";
import { useState } from "react";
import { apiFetch } from "@/lib/api-client";

export type AdminTeacherOption = {
  id: string;
  name: string;
  email: string;
  research_theme: string | null;
  photo_url: string | null;
  is_active: boolean;
};

export type AdminSeminarMaterial = {
  id: string;
  url: string;
  type: "slide" | "pdf" | "video";
};

export type AdminSeminar = {
  id: string;
  name: string;
  description: string | null;
  photo_url: string | null;
  teachers: { id: string; name: string }[];
  materials: AdminSeminarMaterial[];
};

const MATERIAL_TYPE_LABEL: Record<AdminSeminarMaterial["type"], string> = {
  slide: "スライド",
  pdf: "PDF",
  video: "動画",
};

async function extractErrorDetail(res: Response): Promise<string> {
  try {
    const body = (await res.json()) as { detail?: string };
    return body.detail ?? "エラーが発生しました。";
  } catch {
    return "エラーが発生しました。";
  }
}

type AdminSeminarsViewProps = {
  initialSeminars: AdminSeminar[];
  teacherOptions: AdminTeacherOption[];
};

export function AdminSeminarsView({
  initialSeminars,
  teacherOptions,
}: AdminSeminarsViewProps) {
  const { data: session } = useSession();
  const [seminars, setSeminars] = useState(initialSeminars);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const [isCreateFormOpen, setIsCreateFormOpen] = useState(false);
  const [newName, setNewName] = useState("");
  const [newDescription, setNewDescription] = useState("");
  const [newPhotoUrl, setNewPhotoUrl] = useState("");
  const [isCreating, setIsCreating] = useState(false);

  const [editingId, setEditingId] = useState<string | null>(null);
  const [editName, setEditName] = useState("");
  const [editDescription, setEditDescription] = useState("");
  const [editPhotoUrl, setEditPhotoUrl] = useState("");
  const [isSavingEdit, setIsSavingEdit] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [pendingTeacherKey, setPendingTeacherKey] = useState<string | null>(
    null,
  );

  const [materialUrlInputs, setMaterialUrlInputs] = useState<
    Record<string, string>
  >({});
  const [materialTypeInputs, setMaterialTypeInputs] = useState<
    Record<string, AdminSeminarMaterial["type"]>
  >({});
  const [addingMaterialId, setAddingMaterialId] = useState<string | null>(null);
  const [deletingMaterialKey, setDeletingMaterialKey] = useState<string | null>(
    null,
  );

  function openCreateForm(): void {
    setIsCreateFormOpen(true);
    setErrorMessage(null);
  }

  function cancelCreate(): void {
    setIsCreateFormOpen(false);
    setNewName("");
    setNewDescription("");
    setNewPhotoUrl("");
    setErrorMessage(null);
  }

  async function handleCreate(): Promise<void> {
    setErrorMessage(null);
    if (newName.trim() === "") {
      setErrorMessage("ゼミ名を入力してください。");
      return;
    }
    setIsCreating(true);
    try {
      const res = await apiFetch("/admin/seminars", session, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: newName,
          description: newDescription === "" ? null : newDescription,
          photo_url: newPhotoUrl === "" ? null : newPhotoUrl,
        }),
      });
      if (!res.ok) {
        setErrorMessage(await extractErrorDetail(res));
        return;
      }
      const created = (await res.json()) as AdminSeminar;
      setSeminars((prev) => [...prev, created]);
      setNewName("");
      setNewDescription("");
      setNewPhotoUrl("");
      setIsCreateFormOpen(false);
    } catch {
      setErrorMessage("通信に失敗しました。時間をおいて再度お試しください。");
    } finally {
      setIsCreating(false);
    }
  }

  function startEdit(seminar: AdminSeminar): void {
    setEditingId(seminar.id);
    setEditName(seminar.name);
    setEditDescription(seminar.description ?? "");
    setEditPhotoUrl(seminar.photo_url ?? "");
    setErrorMessage(null);
  }

  function cancelEdit(): void {
    setEditingId(null);
  }

  async function handleSaveEdit(seminarId: string): Promise<void> {
    setErrorMessage(null);
    if (editName.trim() === "") {
      setErrorMessage("ゼミ名を入力してください。");
      return;
    }
    setIsSavingEdit(true);
    try {
      const res = await apiFetch(`/admin/seminars/${seminarId}`, session, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: editName,
          description: editDescription === "" ? null : editDescription,
          photo_url: editPhotoUrl === "" ? null : editPhotoUrl,
        }),
      });
      if (!res.ok) {
        setErrorMessage(await extractErrorDetail(res));
        return;
      }
      const updated = (await res.json()) as AdminSeminar;
      setSeminars((prev) =>
        prev.map((s) => (s.id === seminarId ? updated : s)),
      );
      setEditingId(null);
    } catch {
      setErrorMessage("通信に失敗しました。時間をおいて再度お試しください。");
    } finally {
      setIsSavingEdit(false);
    }
  }

  async function handleDelete(seminar: AdminSeminar): Promise<void> {
    const confirmed = window.confirm(
      `「${seminar.name}」を削除します。担当割当・募集設定・所属ゼミ生の記録・紹介資料もすべて削除されます。よろしいですか?`,
    );
    if (!confirmed) {
      return;
    }
    setErrorMessage(null);
    setDeletingId(seminar.id);
    try {
      const res = await apiFetch(`/admin/seminars/${seminar.id}`, session, {
        method: "DELETE",
      });
      if (!res.ok && res.status !== 204) {
        setErrorMessage(await extractErrorDetail(res));
        return;
      }
      setSeminars((prev) => prev.filter((s) => s.id !== seminar.id));
    } catch {
      setErrorMessage("通信に失敗しました。時間をおいて再度お試しください。");
    } finally {
      setDeletingId(null);
    }
  }

  async function handleToggleTeacher(
    seminar: AdminSeminar,
    teacher: AdminTeacherOption,
    isAssigned: boolean,
  ): Promise<void> {
    const key = `${seminar.id}:${teacher.id}`;
    setErrorMessage(null);
    setPendingTeacherKey(key);
    try {
      const res = await apiFetch(
        `/admin/seminars/${seminar.id}/teachers/${teacher.id}`,
        session,
        { method: isAssigned ? "DELETE" : "POST" },
      );
      if (!res.ok) {
        setErrorMessage(await extractErrorDetail(res));
        return;
      }
      setSeminars((prev) =>
        prev.map((s) => {
          if (s.id !== seminar.id) {
            return s;
          }
          const teachers = isAssigned
            ? s.teachers.filter((t) => t.id !== teacher.id)
            : [...s.teachers, { id: teacher.id, name: teacher.name }];
          return { ...s, teachers };
        }),
      );
    } catch {
      setErrorMessage("通信に失敗しました。時間をおいて再度お試しください。");
    } finally {
      setPendingTeacherKey(null);
    }
  }

  async function handleAddMaterial(seminarId: string): Promise<void> {
    const url = (materialUrlInputs[seminarId] ?? "").trim();
    setErrorMessage(null);
    if (url === "") {
      setErrorMessage("資料のURLを入力してください。");
      return;
    }
    const type = materialTypeInputs[seminarId] ?? "slide";
    setAddingMaterialId(seminarId);
    try {
      const res = await apiFetch(
        `/admin/seminars/${seminarId}/materials`,
        session,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ url, type }),
        },
      );
      if (!res.ok) {
        setErrorMessage(await extractErrorDetail(res));
        return;
      }
      const created = (await res.json()) as AdminSeminarMaterial;
      setSeminars((prev) =>
        prev.map((s) =>
          s.id === seminarId
            ? { ...s, materials: [...s.materials, created] }
            : s,
        ),
      );
      setMaterialUrlInputs((prev) => ({ ...prev, [seminarId]: "" }));
    } catch {
      setErrorMessage("通信に失敗しました。時間をおいて再度お試しください。");
    } finally {
      setAddingMaterialId(null);
    }
  }

  async function handleDeleteMaterial(
    seminarId: string,
    materialId: string,
  ): Promise<void> {
    const key = `${seminarId}:${materialId}`;
    setErrorMessage(null);
    setDeletingMaterialKey(key);
    try {
      const res = await apiFetch(
        `/admin/seminars/${seminarId}/materials/${materialId}`,
        session,
        { method: "DELETE" },
      );
      if (!res.ok && res.status !== 204) {
        setErrorMessage(await extractErrorDetail(res));
        return;
      }
      setSeminars((prev) =>
        prev.map((s) =>
          s.id === seminarId
            ? {
                ...s,
                materials: s.materials.filter((m) => m.id !== materialId),
              }
            : s,
        ),
      );
    } catch {
      setErrorMessage("通信に失敗しました。時間をおいて再度お試しください。");
    } finally {
      setDeletingMaterialKey(null);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <p className="text-sm text-foreground/60">
        募集人数・対象学年の設定は
        <Link
          href="/admin/recruitment-terms"
          className="underline hover:opacity-70"
        >
          募集ラウンド管理
        </Link>
        画面で行います。
      </p>

      {errorMessage && (
        <p className="rounded-lg border border-black/[.08] p-4 text-sm dark:border-white/[.145]">
          {errorMessage}
        </p>
      )}

      {isCreateFormOpen ? (
        <section className="rounded-lg border border-black/[.08] p-4 dark:border-white/[.145]">
          <h2 className="font-semibold">新規ゼミ作成</h2>
          <div className="mt-3 flex flex-col gap-2">
            <input
              type="text"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              placeholder="ゼミ名"
              className="w-full rounded-lg border border-black/[.08] bg-background px-3 py-2 text-sm dark:border-white/[.145]"
            />
            <textarea
              value={newDescription}
              onChange={(e) => setNewDescription(e.target.value)}
              placeholder="説明(任意)"
              rows={2}
              className="w-full rounded-lg border border-black/[.08] bg-background px-3 py-2 text-sm dark:border-white/[.145]"
            />
            <input
              type="text"
              value={newPhotoUrl}
              onChange={(e) => setNewPhotoUrl(e.target.value)}
              placeholder="アイコン画像のURL(任意)"
              className="w-full rounded-lg border border-black/[.08] bg-background px-3 py-2 text-sm dark:border-white/[.145]"
            />
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
          + 新規ゼミを作成
        </button>
      )}

      <div className="flex flex-col gap-4">
        {seminars.map((seminar) => {
          const isEditing = editingId === seminar.id;
          const assignedIds = new Set(seminar.teachers.map((t) => t.id));

          return (
            <section
              key={seminar.id}
              className="rounded-lg border border-black/[.08] p-4 dark:border-white/[.145]"
            >
              {isEditing ? (
                <div className="flex flex-col gap-2">
                  <input
                    type="text"
                    value={editName}
                    onChange={(e) => setEditName(e.target.value)}
                    className="w-full rounded-lg border border-black/[.08] bg-background px-3 py-2 text-sm dark:border-white/[.145]"
                  />
                  <textarea
                    value={editDescription}
                    onChange={(e) => setEditDescription(e.target.value)}
                    rows={2}
                    className="w-full rounded-lg border border-black/[.08] bg-background px-3 py-2 text-sm dark:border-white/[.145]"
                  />
                  <input
                    type="text"
                    value={editPhotoUrl}
                    onChange={(e) => setEditPhotoUrl(e.target.value)}
                    placeholder="アイコン画像のURL(任意)"
                    className="w-full rounded-lg border border-black/[.08] bg-background px-3 py-2 text-sm dark:border-white/[.145]"
                  />
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={() => handleSaveEdit(seminar.id)}
                      disabled={isSavingEdit}
                      className="rounded-full bg-foreground px-4 py-2 text-sm font-medium text-background hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      {isSavingEdit ? "保存中..." : "保存する"}
                    </button>
                    <button
                      type="button"
                      onClick={cancelEdit}
                      disabled={isSavingEdit}
                      className="rounded-full border border-black/[.08] px-4 py-2 text-sm font-medium hover:bg-black/[.04] dark:border-white/[.145] dark:hover:bg-white/[.08]"
                    >
                      キャンセル
                    </button>
                  </div>
                </div>
              ) : (
                <div className="flex items-start justify-between gap-4">
                  <div className="flex gap-3">
                    {seminar.photo_url && (
                      // biome-ignore lint/performance/noImgElement: photo_urlは任意の外部ドメインのため next/image のドメイン許可設定が不要なimgタグを使う
                      <img
                        src={seminar.photo_url}
                        alt={seminar.name}
                        className="h-12 w-12 shrink-0 rounded-full object-cover"
                      />
                    )}
                    <div>
                      <p className="font-semibold">{seminar.name}</p>
                      <p className="mt-1 whitespace-pre-wrap text-sm text-foreground/70">
                        {seminar.description ?? "説明は未設定です。"}
                      </p>
                      <p className="mt-1 text-xs text-foreground/40">
                        ID(配属結果CSVのseminar_id列に使用):{" "}
                        <code className="select-all">{seminar.id}</code>
                      </p>
                    </div>
                  </div>
                  <div className="flex shrink-0 gap-2">
                    <button
                      type="button"
                      onClick={() => startEdit(seminar)}
                      className="rounded-full border border-black/[.08] px-3 py-1.5 text-xs font-medium hover:bg-black/[.04] dark:border-white/[.145] dark:hover:bg-white/[.08]"
                    >
                      編集
                    </button>
                    <button
                      type="button"
                      onClick={() => handleDelete(seminar)}
                      disabled={deletingId === seminar.id}
                      className="rounded-full border border-black/[.08] px-3 py-1.5 text-xs font-medium text-red-600 hover:bg-black/[.04] disabled:cursor-not-allowed disabled:opacity-50 dark:border-white/[.145] dark:text-red-400 dark:hover:bg-white/[.08]"
                    >
                      {deletingId === seminar.id ? "削除中..." : "削除"}
                    </button>
                  </div>
                </div>
              )}

              <div className="mt-3">
                <p className="text-sm text-foreground/60">担当教員</p>
                {teacherOptions.length === 0 ? (
                  <p className="mt-1 text-sm text-foreground/40">
                    教員が登録されていません。
                  </p>
                ) : (
                  <div className="mt-2 flex flex-wrap gap-3">
                    {teacherOptions.map((teacher) => {
                      const isAssigned = assignedIds.has(teacher.id);
                      const key = `${seminar.id}:${teacher.id}`;
                      return (
                        <label
                          key={teacher.id}
                          className="flex items-center gap-1.5 text-sm"
                        >
                          <input
                            type="checkbox"
                            checked={isAssigned}
                            disabled={pendingTeacherKey === key}
                            onChange={() =>
                              handleToggleTeacher(seminar, teacher, isAssigned)
                            }
                          />
                          {teacher.name}
                          {!teacher.is_active && (
                            <span className="text-xs text-foreground/40">
                              (無効)
                            </span>
                          )}
                        </label>
                      );
                    })}
                  </div>
                )}
              </div>

              <div className="mt-3">
                <p className="text-sm text-foreground/60">紹介資料</p>
                {seminar.materials.length === 0 ? (
                  <p className="mt-1 text-sm text-foreground/40">
                    資料はまだありません。
                  </p>
                ) : (
                  <ul className="mt-2 flex flex-col gap-1">
                    {seminar.materials.map((material) => {
                      const materialKey = `${seminar.id}:${material.id}`;
                      return (
                        <li
                          key={material.id}
                          className="flex items-center gap-2 text-sm"
                        >
                          <span className="shrink-0 text-xs text-foreground/40">
                            {MATERIAL_TYPE_LABEL[material.type]}
                          </span>
                          <a
                            href={material.url}
                            target="_blank"
                            rel="noreferrer"
                            className="truncate underline hover:opacity-70"
                          >
                            {material.url}
                          </a>
                          <button
                            type="button"
                            onClick={() =>
                              handleDeleteMaterial(seminar.id, material.id)
                            }
                            disabled={deletingMaterialKey === materialKey}
                            className="shrink-0 text-xs text-red-600 hover:opacity-70 disabled:cursor-not-allowed disabled:opacity-50 dark:text-red-400"
                          >
                            削除
                          </button>
                        </li>
                      );
                    })}
                  </ul>
                )}
                <div className="mt-2 flex flex-wrap gap-2">
                  <select
                    value={materialTypeInputs[seminar.id] ?? "slide"}
                    onChange={(e) =>
                      setMaterialTypeInputs((prev) => ({
                        ...prev,
                        [seminar.id]: e.target
                          .value as AdminSeminarMaterial["type"],
                      }))
                    }
                    className="rounded-lg border border-black/[.08] bg-background px-2 py-1.5 text-sm dark:border-white/[.145]"
                  >
                    <option value="slide">スライド</option>
                    <option value="pdf">PDF</option>
                    <option value="video">動画</option>
                  </select>
                  <input
                    type="text"
                    value={materialUrlInputs[seminar.id] ?? ""}
                    onChange={(e) =>
                      setMaterialUrlInputs((prev) => ({
                        ...prev,
                        [seminar.id]: e.target.value,
                      }))
                    }
                    placeholder="資料のURL"
                    className="min-w-0 flex-1 rounded-lg border border-black/[.08] bg-background px-3 py-1.5 text-sm dark:border-white/[.145]"
                  />
                  <button
                    type="button"
                    onClick={() => handleAddMaterial(seminar.id)}
                    disabled={addingMaterialId === seminar.id}
                    className="shrink-0 rounded-full border border-black/[.08] px-3 py-1.5 text-xs font-medium hover:bg-black/[.04] disabled:cursor-not-allowed disabled:opacity-50 dark:border-white/[.145] dark:hover:bg-white/[.08]"
                  >
                    {addingMaterialId === seminar.id ? "追加中..." : "追加"}
                  </button>
                </div>
              </div>
            </section>
          );
        })}
      </div>
    </div>
  );
}
