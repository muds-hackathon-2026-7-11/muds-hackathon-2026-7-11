"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { signOut } from "next-auth/react";
import { useEffect, useRef, useState } from "react";

const navItems = [
  { label: "マイページ", href: "/" },
  { label: "志望理由提出", href: "/apply" },
  { label: "志望状況一覧", href: "/assignment" },
] as const;

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
  const settingsRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!isSettingsOpen) {
      return;
    }
    function handleClickOutside(e: MouseEvent): void {
      if (!settingsRef.current?.contains(e.target as Node)) {
        setIsSettingsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [isSettingsOpen]);

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

        <Link
          href="/chat"
          aria-label="AIゼミ相談"
          title="AIゼミ相談"
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
            <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z" />
          </svg>
        </Link>

        <div ref={settingsRef} className="relative">
          <button
            type="button"
            onClick={() => setIsSettingsOpen((open) => !open)}
            aria-label="設定"
            aria-expanded={isSettingsOpen}
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
            <div className="absolute right-0 top-full z-50 mt-2 w-48 rounded-xl border border-[#e6e6e6] bg-white py-1 shadow-lg shadow-black/[.08]">
              {isAdmin && (
                <Link
                  href="/admin"
                  onClick={() => setIsSettingsOpen(false)}
                  className="block px-4 py-2 text-sm text-zinc-700 hover:bg-[#e6e6e6]/60"
                >
                  管理者画面
                </Link>
              )}
              <button
                type="button"
                onClick={() => signOut()}
                className="block w-full px-4 py-2 text-left text-sm text-zinc-700 hover:bg-[#e6e6e6]/60"
              >
                ログアウト
              </button>
            </div>
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
        </nav>
      )}
    </header>
  );
}
