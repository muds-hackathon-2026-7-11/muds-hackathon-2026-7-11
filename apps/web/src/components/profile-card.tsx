type ProfileCardProps = {
  name: string;
  email: string;
  grade: string | null;
  researchTheme: string | null;
};

export function ProfileCard({
  name,
  email,
  grade,
  researchTheme,
}: ProfileCardProps) {
  return (
    <section className="rounded-2xl border-2 border-[#add8e6] bg-white p-6 shadow-sm shadow-[#add8e6]/30">
      <div className="border-b border-[#add8e6]/40 pb-5">
        <p className="text-xs font-semibold uppercase tracking-wider text-zinc-400">
          Profile
        </p>
        <p className="mt-2 text-2xl font-bold text-zinc-800">{name}</p>
        <p className="text-sm text-zinc-500">{email}</p>
        <p className="text-sm text-zinc-500">{grade ?? "未設定"}</p>
      </div>

      <div className="pt-5">
        <p className="text-xs font-semibold uppercase tracking-wider text-zinc-400">
          Research Summary
        </p>
        <p className="mt-2 whitespace-pre-wrap text-zinc-700">
          {researchTheme ?? "未設定"}
        </p>
        <button
          type="button"
          disabled
          title="準備中"
          className="mt-4 inline-flex cursor-not-allowed items-center gap-1.5 rounded-full bg-[#add8e6]/50 px-4 py-1.5 text-sm font-medium text-sky-900/60"
        >
          編集
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth={2}
            strokeLinecap="round"
            strokeLinejoin="round"
            className="h-3.5 w-3.5"
            aria-hidden="true"
          >
            <path d="M12 20h9" />
            <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4Z" />
          </svg>
        </button>
      </div>
    </section>
  );
}
