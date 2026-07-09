"use client";

import { useSession } from "next-auth/react";
import { useState } from "react";
import { apiFetch } from "@/lib/api-client";

export type TeacherSeminarMaterial = {
  id: string;
  url: string;
  type: "slide" | "pdf" | "video";
};

export type TeacherSeminar = {
  id: string;
  name: string;
  description: string | null;
  photo_url: string | null;
  materials: TeacherSeminarMaterial[];
};

const MATERIAL_TYPE_LABEL: Record<TeacherSeminarMaterial["type"], string> = {
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

type TeacherSeminarViewProps = {
  initialSeminars: TeacherSeminar[];
};

export function TeacherSeminarView({
  initialSeminars,
}: TeacherSeminarViewProps) {
  const { data: session } = useSession();
  const [seminars, setSeminars] = useState(initialSeminars);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const [editingId, setEditingId] = useState<string | null>(null);
  const [editDescription, setEditDescription] = useState("");
  const [editPhotoUrl, setEditPhotoUrl] = useState("");
  const [isSaving, setIsSaving] = useState(false);

  const [materialUrlInputs, setMaterialUrlInputs] = useState<
    Record<string, string>
  >({});
  const [materialTypeInputs, setMaterialTypeInputs] = useState<
    Record<string, TeacherSeminarMaterial["type"]>
  >({});
  const [addingMaterialId, setAddingMaterialId] = useState<string | null>(null);
  const [deletingMaterialKey, setDeletingMaterialKey] = useState<string | null>(
    null,
  );

  function startEdit(seminar: TeacherSeminar): void {
    setEditingId(seminar.id);
    setEditDescription(seminar.description ?? "");
    setEditPhotoUrl(seminar.photo_url ?? "");
    setErrorMessage(null);
  }

  function cancelEdit(): void {
    setEditingId(null);
  }

  async function handleSaveEdit(seminarId: string): Promise<void> {
    setErrorMessage(null);
    setIsSaving(true);
    try {
      const res = await apiFetch(`/teacher/seminars/${seminarId}`, session, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          description: editDescription === "" ? null : editDescription,
          photo_url: editPhotoUrl === "" ? null : editPhotoUrl,
        }),
      });
      if (!res.ok) {
        setErrorMessage(await extractErrorDetail(res));
        return;
      }
      const updated = (await res.json()) as TeacherSeminar;
      setSeminars((prev) =>
        prev.map((s) => (s.id === seminarId ? updated : s)),
      );
      setEditingId(null);
    } catch {
      setErrorMessage("通信に失敗しました。時間をおいて再度お試しください。");
    } finally {
      setIsSaving(false);
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
        `/teacher/seminars/${seminarId}/materials`,
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
      const created = (await res.json()) as TeacherSeminarMaterial;
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
        `/teacher/seminars/${seminarId}/materials/${materialId}`,
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
      {errorMessage && (
        <p className="rounded-2xl border-2 border-red-300 bg-white p-4 text-sm text-red-600 shadow-sm">
          {errorMessage}
        </p>
      )}

      {seminars.length === 0 ? (
        <p className="text-sm text-zinc-500">担当しているゼミがありません。</p>
      ) : (
        seminars.map((seminar) => {
          const isEditing = editingId === seminar.id;
          return (
            <section
              key={seminar.id}
              className="rounded-2xl border-2 border-[#add8e6] bg-white p-6 shadow-sm shadow-[#add8e6]/30"
            >
              <h2 className="text-lg font-bold text-zinc-900">
                {seminar.name}
              </h2>

              {isEditing ? (
                <div className="mt-3 flex flex-col gap-2">
                  <textarea
                    value={editDescription}
                    onChange={(e) => setEditDescription(e.target.value)}
                    placeholder="研究内容・ゼミ紹介文"
                    rows={4}
                    className="w-full rounded-lg border border-[#add8e6]/60 bg-white px-3 py-2 text-sm text-zinc-800 focus:border-[#add8e6] focus:outline-none focus-visible:ring-2 focus-visible:ring-[#add8e6]/50"
                  />
                  <input
                    type="text"
                    value={editPhotoUrl}
                    onChange={(e) => setEditPhotoUrl(e.target.value)}
                    placeholder="研究室写真のURL(任意)"
                    className="w-full rounded-lg border border-[#add8e6]/60 bg-white px-3 py-2 text-sm text-zinc-800 focus:border-[#add8e6] focus:outline-none focus-visible:ring-2 focus-visible:ring-[#add8e6]/50"
                  />
                  <div className="mt-1 flex gap-2">
                    <button
                      type="button"
                      onClick={() => handleSaveEdit(seminar.id)}
                      disabled={isSaving}
                      className="rounded-full bg-[#add8e6] px-5 py-2 text-sm font-semibold text-sky-950 shadow-sm transition-all hover:bg-[#9bcfe0] hover:shadow active:translate-y-px disabled:cursor-not-allowed disabled:opacity-50 focus:outline-none focus-visible:ring-4 focus-visible:ring-[#add8e6]/50"
                    >
                      {isSaving ? "保存中..." : "保存する"}
                    </button>
                    <button
                      type="button"
                      onClick={cancelEdit}
                      disabled={isSaving}
                      className="rounded-full border border-[#e6e6e6] bg-white px-5 py-2 text-sm font-medium text-zinc-600 hover:bg-[#e6e6e6]/50 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      キャンセル
                    </button>
                  </div>
                </div>
              ) : (
                <div className="mt-3 flex items-start justify-between gap-4">
                  <div className="flex gap-3">
                    {seminar.photo_url && (
                      // biome-ignore lint/performance/noImgElement: photo_urlは任意の外部ドメインのため next/image のドメイン許可設定が不要なimgタグを使う
                      <img
                        src={seminar.photo_url}
                        alt={seminar.name}
                        className="h-16 w-16 shrink-0 rounded-full object-cover"
                      />
                    )}
                    {seminar.description && (
                      <p className="whitespace-pre-wrap text-sm text-zinc-700">
                        {seminar.description}
                      </p>
                    )}
                  </div>
                  <button
                    type="button"
                    onClick={() => startEdit(seminar)}
                    className="shrink-0 rounded-full border border-[#add8e6]/60 px-3 py-1.5 text-xs font-medium text-zinc-700 transition-colors hover:bg-[#add8e6]/10"
                  >
                    編集
                  </button>
                </div>
              )}

              <div className="mt-4 border-t border-[#add8e6]/40 pt-3">
                <p className="text-sm font-semibold text-zinc-700">紹介資料</p>
                {seminar.materials.length === 0 ? (
                  <p className="mt-1 text-sm text-zinc-500">
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
                          <span className="shrink-0 text-xs text-zinc-400">
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
                            className="shrink-0 text-xs text-red-600 hover:opacity-70 disabled:cursor-not-allowed disabled:opacity-50"
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
                          .value as TeacherSeminarMaterial["type"],
                      }))
                    }
                    className="rounded-lg border border-[#add8e6]/60 bg-white px-2 py-1.5 text-sm"
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
                    className="min-w-0 flex-1 rounded-lg border border-[#add8e6]/60 bg-white px-3 py-1.5 text-sm"
                  />
                  <button
                    type="button"
                    onClick={() => handleAddMaterial(seminar.id)}
                    disabled={addingMaterialId === seminar.id}
                    className="shrink-0 rounded-full bg-[#add8e6] px-5 py-2 text-sm font-semibold text-sky-950 shadow-sm transition-all hover:bg-[#9bcfe0] disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {addingMaterialId === seminar.id ? "追加中..." : "追加"}
                  </button>
                </div>
              </div>
            </section>
          );
        })
      )}
    </div>
  );
}
