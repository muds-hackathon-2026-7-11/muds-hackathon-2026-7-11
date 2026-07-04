type AuthMenuBarProps = {
  current: "mypage" | "haizoku";
};

const menuItems = [
  {
    key: "mypage",
    label: "マイページ",
    href: "/mypage",
  },
  {
    key: "haizoku",
    label: "配属状況",
    href: "/haizoku",
  },
] as const;

export function AuthMenuBar({ current }: AuthMenuBarProps) {
  return (
    <nav className="flex flex-wrap items-center gap-2 rounded-full border border-slate-200 bg-white/90 p-2 shadow-[0_10px_30px_rgba(15,23,42,0.08)] backdrop-blur">
      {menuItems.map((item) => {
        const isActive = item.key === current;

        return (
          <a
            key={item.key}
            className={[
              "inline-flex items-center rounded-full px-4 py-2 text-sm font-semibold transition",
              isActive
                ? "bg-slate-950 text-white shadow-sm"
                : "text-slate-600 hover:bg-slate-100 hover:text-slate-950",
            ].join(" ")}
            href={item.href}
          >
            {item.label}
          </a>
        );
      })}
    </nav>
  );
}