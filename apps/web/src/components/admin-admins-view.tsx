"use client";

import { useSession } from "next-auth/react";
import { useState } from "react";
import { apiFetch } from "@/lib/api-client";

export type AdminUser = {
  id: string;
  name: string;
  email: string;
  is_active: boolean;
};

type AdminUserCandidate = {
  id: string;
  name: string;
  email: string;
  role: "student" | "teacher" | "admin";
};

async function extractErrorDetail(res: Response): Promise<string> {
  try {
    const body = (await res.json()) as { detail?: string };
    return body.detail ?? "エラーが発生しました。";
  } catch {
    return "エラーが発生しました。";
  }
}

type AdminAdminsViewProps = {
  initialAdmins: AdminUser[];
};

export function AdminAdminsView({ initialAdmins }: AdminAdminsViewProps) {
  const { data: session } = useSession();
  const [admins, setAdmins] = useState(initialAdmins);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const [isCreateFormOpen, setIsCreateFormOpen] = useState(false);
  const [newEmail, setNewEmail] = useState("");
  const [isLookingUp, setIsLookingUp] = useState(false);
  // メールアドレスの確認(下見)で見つかった候補者。確定後に追加を実行する。
  const [candidate, setCandidate] = useState<AdminUserCandidate | null>(null);
  const [isCreating, setIsCreating] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  function openCreateForm(): void {
    setIsCreateFormOpen(true);
    setErrorMessage(null);
  }

  function cancelCreate(): void {
    setIsCreateFormOpen(false);
    setNewEmail("");
    setCandidate(null);
    setErrorMessage(null);
  }

  async function handleLookup(): Promise<void> {
    setErrorMessage(null);
    setCandidate(null);
    if (newEmail.trim() === "") {
      setErrorMessage("メールアドレスを入力してください。");
      return;
    }
    setIsLookingUp(true);
    try {
      const res = await apiFetch(
        `/admin/admins/lookup?email=${encodeURIComponent(newEmail.trim())}`,
        session,
      );
      if (!res.ok) {
        setErrorMessage(
          res.status === 404
            ? "無効なメールアドレスです(登録されているユーザーが見つかりません)。"
            : await extractErrorDetail(res),
        );
        return;
      }
      setCandidate((await res.json()) as AdminUserCandidate);
    } catch {
      setErrorMessage("通信に失敗しました。時間をおいて再度お試しください。");
    } finally {
      setIsLookingUp(false);
    }
  }

  async function handleConfirmCreate(): Promise<void> {
    if (!candidate) {
      return;
    }
    setErrorMessage(null);
    setIsCreating(true);
    try {
      const res = await apiFetch("/admin/admins", session, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: candidate.email }),
      });
      if (!res.ok) {
        setErrorMessage(await extractErrorDetail(res));
        return;
      }
      const created = (await res.json()) as AdminUser;
      setAdmins((prev) => [...prev, created]);
      cancelCreate();
    } catch {
      setErrorMessage("通信に失敗しました。時間をおいて再度お試しください。");
    } finally {
      setIsCreating(false);
    }
  }

  async function handleDelete(admin: AdminUser): Promise<void> {
    const confirmed = window.confirm(
      `「${admin.name}」の管理者権限を外します(通常の学生に戻ります)。よろしいですか?`,
    );
    if (!confirmed) {
      return;
    }
    setErrorMessage(null);
    setDeletingId(admin.id);
    try {
      const res = await apiFetch(`/admin/admins/${admin.id}`, session, {
        method: "DELETE",
      });
      if (!res.ok) {
        setErrorMessage(await extractErrorDetail(res));
        return;
      }
      setAdmins((prev) => prev.filter((a) => a.id !== admin.id));
    } catch {
      setErrorMessage("通信に失敗しました。時間をおいて再度お試しください。");
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      {!isCreateFormOpen && errorMessage && (
        <p className="rounded-lg border border-[#add8e6]/60 bg-white p-4 text-sm">
          {errorMessage}
        </p>
      )}

      <button
        type="button"
        onClick={openCreateForm}
        className="self-start rounded-full bg-[#add8e6] px-4 py-2 text-sm font-semibold text-sky-950 shadow-sm transition-all hover:bg-[#9bcfe0]"
      >
        + 管理者を追加
      </button>

      {isCreateFormOpen && (
        // biome-ignore lint/a11y/noStaticElementInteractions: 背景クリックで閉じるための領域
        // biome-ignore lint/a11y/useKeyWithClickEvents: 閉じるはキャンセルボタンで代替する
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
          onClick={(e) => {
            if (e.target === e.currentTarget && !isCreating && !isLookingUp) {
              cancelCreate();
            }
          }}
        >
          <section
            role="dialog"
            aria-modal="true"
            aria-label="管理者を追加"
            className="w-full max-w-lg rounded-2xl border border-line bg-white p-6 shadow-lg shadow-[#add8e6]/30"
          >
            <h2 className="text-lg font-bold text-zinc-900">管理者を追加</h2>
            <p className="mt-1 text-sm text-zinc-600">
              既に登録されている学生のメールアドレスを入力してください(教員は選べません)。
            </p>
            {errorMessage && (
              <p className="mt-3 rounded-lg border border-[#add8e6]/60 bg-white p-3 text-sm">
                {errorMessage}
              </p>
            )}
            <div className="mt-4 flex flex-col gap-2">
              {candidate ? (
                <>
                  <div className="rounded-lg border border-[#add8e6]/60 bg-[#add8e6]/10 p-3">
                    <p className="text-sm text-zinc-600">
                      この人を管理者にします
                    </p>
                    <p className="mt-1 font-semibold text-zinc-900">
                      {candidate.name}
                    </p>
                    <p className="text-sm text-zinc-600">{candidate.email}</p>
                  </div>
                  <div className="mt-2 flex gap-2">
                    <button
                      type="button"
                      onClick={handleConfirmCreate}
                      disabled={isCreating}
                      className="rounded-full bg-[#add8e6] px-5 py-2 text-sm font-semibold text-sky-950 shadow-sm transition-all hover:bg-[#9bcfe0] disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      {isCreating ? "追加中..." : "この人を追加する"}
                    </button>
                    <button
                      type="button"
                      onClick={() => setCandidate(null)}
                      disabled={isCreating}
                      className="rounded-full border border-[#e6e6e6] bg-white px-5 py-2 text-sm font-medium text-zinc-600 hover:bg-[#e6e6e6]/50 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      戻る
                    </button>
                  </div>
                </>
              ) : (
                <>
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
                      onClick={handleLookup}
                      disabled={isLookingUp}
                      className="rounded-full bg-[#add8e6] px-5 py-2 text-sm font-semibold text-sky-950 shadow-sm transition-all hover:bg-[#9bcfe0] disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      {isLookingUp ? "確認中..." : "確認する"}
                    </button>
                    <button
                      type="button"
                      onClick={cancelCreate}
                      disabled={isLookingUp}
                      className="rounded-full border border-[#e6e6e6] bg-white px-5 py-2 text-sm font-medium text-zinc-600 hover:bg-[#e6e6e6]/50 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      キャンセル
                    </button>
                  </div>
                </>
              )}
            </div>
          </section>
        </div>
      )}

      <div className="flex flex-col gap-3">
        {admins.length === 0 ? (
          <p className="text-sm text-zinc-600">管理者がまだいません。</p>
        ) : (
          admins.map((admin) => (
            <section
              key={admin.id}
              className="flex items-center justify-between gap-4 rounded-lg border border-[#add8e6]/60 bg-white p-4"
            >
              <div>
                <p className="font-semibold text-zinc-900">
                  {admin.name}
                  {!admin.is_active && (
                    <span className="ml-2 text-xs font-normal text-zinc-600">
                      (無効)
                    </span>
                  )}
                </p>
                <p className="text-sm text-zinc-600">{admin.email}</p>
              </div>
              <button
                type="button"
                onClick={() => handleDelete(admin)}
                disabled={deletingId === admin.id}
                className="shrink-0 rounded-full border border-[#add8e6]/60 px-3 py-1.5 text-xs font-medium text-red-600 hover:bg-[#add8e6]/10 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {deletingId === admin.id ? "削除中..." : "削除"}
              </button>
            </section>
          ))
        )}
      </div>
    </div>
  );
}
