"use client";

import { signOut } from "next-auth/react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

const baseNavItems = [
  { label: "マイページ", href: "/" },
  { label: "志望理由提出", href: "/apply" },
  { label: "応募状況", href: "/assignment" },
] as const;

const adminNavItem = { label: "管理者", href: "/admin" } as const;

function isNavItemActive(pathname: string, href: string): boolean {
  return href === "/" ? pathname === "/" : pathname.startsWith(href);
}

function navLinkClassName(isActive: boolean): string {
  return [
    "rounded-full px-4 py-2 text-sm font-medium transition-colors",
    isActive
      ? "bg-[#e6e6e6] text-zinc-900"
      : "text-zinc-500 hover:bg-[#e6e6e6]/60 hover:text-zinc-900",
  ].join(" ");
}

type MenuBarProps = {
  isAdmin: boolean;
};

export function MenuBar({ isAdmin }: MenuBarProps) {
  const pathname = usePathname();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const navItems = baseNavItems;

  return (
    <header className="relative z-40 border-b border-[#e6e6e6] bg-white">
      <div className="mx-auto flex h-16 w-full max-w-5xl items-center gap-2 px-4 sm:px-6">
        <Link
          href="/"
          className="text-lg font-semibold tracking-tight text-zinc-900"
        >
          Zemi-Match
        </Link>

        <nav className="ml-auto hidden items-center gap-1 sm:flex">
          {navItems.map((item) => {
            const isActive = isNavItemActive(pathname, item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                aria-current={isActive ? "page" : undefined}
                className={navLinkClassName(isActive)}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>

        <div className="relative hidden sm:block">
          <button
            type="button"
            onClick={() => setIsSettingsOpen((open) => !open)}
            aria-expanded={isSettingsOpen}
            aria-label="設定"
            className="flex h-9 w-9 items-center justify-center rounded-full text-zinc-500 hover:bg-[#e6e6e6]/60 hover:text-zinc-900"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth={2}
              strokeLinecap="round"
              strokeLinejoin="round"
              className="h-5 w-5"
              aria-hidden="true"
            >
              <circle cx="12" cy="12" r="3" />
              <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
            </svg>
          </button>

          {isSettingsOpen && (
            <>
              {/* 外側クリックで閉じるための透明オーバーレイ */}
              {/* biome-ignore lint/a11y/noStaticElementInteractions: 外側クリックで閉じるだけの領域 */}
              {/* biome-ignore lint/a11y/useKeyWithClickEvents: 閉じるのは各メニュー項目/再クリックで代替 */}
              <div
                className="fixed inset-0 z-40"
                onClick={() => setIsSettingsOpen(false)}
              />
              <div className="absolute right-0 top-full z-50 mt-2 w-48 overflow-hidden rounded-xl border border-[#e6e6e6] bg-white py-1 shadow-lg shadow-black/[.08]">
                {isAdmin && (
                  <Link
                    href={adminNavItem.href}
                    onClick={() => setIsSettingsOpen(false)}
                    className="block px-4 py-2 text-sm text-zinc-700 hover:bg-[#e6e6e6]/60"
                  >
                    {adminNavItem.label}画面
                  </Link>
                )}
                <button
                  type="button"
                  onClick={() => {
                    setIsSettingsOpen(false);
                    signOut();
                  }}
                  className="block w-full px-4 py-2 text-left text-sm text-zinc-700 hover:bg-[#e6e6e6]/60"
                >
                  ログアウト
                </button>
              </div>
            </>
          )}
        </div>

        <button
          type="button"
          onClick={() => setIsMobileMenuOpen((open) => !open)}
          aria-expanded={isMobileMenuOpen}
          aria-label="メニューを開閉する"
          className="ml-auto flex h-9 w-9 items-center justify-center rounded-full text-zinc-700 hover:bg-[#e6e6e6]/60 sm:hidden"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth={2}
            strokeLinecap="round"
            strokeLinejoin="round"
            className="h-5 w-5"
            aria-hidden="true"
          >
            {isMobileMenuOpen ? (
              <path d="M18 6 6 18M6 6l12 12" />
            ) : (
              <path d="M4 6h16M4 12h16M4 18h16" />
            )}
          </svg>
        </button>
      </div>

      {isMobileMenuOpen && (
        <nav className="absolute inset-x-0 top-full flex flex-col gap-1 border-b border-[#e6e6e6] bg-white px-4 py-2 shadow-lg shadow-black/[.05] sm:hidden">
          {navItems.map((item) => {
            const isActive = isNavItemActive(pathname, item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                aria-current={isActive ? "page" : undefined}
                onClick={() => setIsMobileMenuOpen(false)}
                className={navLinkClassName(isActive)}
              >
                {item.label}
              </Link>
            );
          })}

          <div className="my-1 border-t border-[#e6e6e6]" />

          {isAdmin && (
            <Link
              href={adminNavItem.href}
              aria-current={
                isNavItemActive(pathname, adminNavItem.href)
                  ? "page"
                  : undefined
              }
              onClick={() => setIsMobileMenuOpen(false)}
              className={navLinkClassName(
                isNavItemActive(pathname, adminNavItem.href),
              )}
            >
              {adminNavItem.label}画面
            </Link>
          )}
          <button
            type="button"
            onClick={() => {
              setIsMobileMenuOpen(false);
              signOut();
            }}
            className="rounded-full px-4 py-2 text-left text-sm font-medium text-zinc-500 transition-colors hover:bg-[#e6e6e6]/60 hover:text-zinc-900"
          >
            ログアウト
          </button>
        </nav>
      )}
    </header>
  );
}
