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
    <section className="rounded-lg border border-black/[.08] p-6 dark:border-white/[.145]">
      <div className="border-b border-black/[.08] pb-4 dark:border-white/[.145]">
        <p className="font-semibold">{name}</p>
        <p className="text-sm text-foreground/60">{email}</p>
        <p className="text-sm text-foreground/60">{grade ?? "未設定"}</p>
      </div>

      <div className="pt-4">
        <p className="text-sm text-foreground/60">研究概要</p>
        <p className="mt-1">{researchTheme ?? "未設定"}</p>
        <button
          type="button"
          disabled
          title="準備中"
          className="mt-4 cursor-not-allowed rounded-full border border-black/[.08] px-4 py-2 text-sm font-medium text-foreground/40 dark:border-white/[.145]"
        >
          編集
        </button>
      </div>
    </section>
  );
}
