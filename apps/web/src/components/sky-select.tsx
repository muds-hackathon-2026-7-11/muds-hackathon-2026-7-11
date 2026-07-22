"use client";

import { useEffect, useId, useRef, useState } from "react";

// ネイティブの<select>は、開いたときの選択肢リスト(特にハイライト色)を
// CSSで変更できない(ブラウザ/OS描画)。基調カラー(白/グレー/水色)に
// 揃えるため、自前のドロップダウンUIを持つセレクトを用意する。
//
// 値の受け渡しはネイティブと同じ「選択肢のvalue文字列」で、呼び出し側は
// <select>とほぼ同じ感覚で使える。

export type SkySelectOption = {
  value: string;
  label: string;
};

type SkySelectProps = {
  value: string;
  options: SkySelectOption[];
  onChange: (value: string) => void;
  ariaLabel?: string;
  className?: string;
};

export function SkySelect({
  value,
  options,
  onChange,
  ariaLabel,
  className,
}: SkySelectProps) {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const listboxId = useId();

  const selectedOption = options.find((option) => option.value === value);

  function selectOption(nextValue: string): void {
    onChange(nextValue);
    setIsOpen(false);
  }

  // 外側クリック・Escで閉じる。
  useEffect(() => {
    if (!isOpen) {
      return;
    }
    function handlePointerDown(event: MouseEvent): void {
      if (
        containerRef.current &&
        !containerRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    }
    function handleKeyDown(event: KeyboardEvent): void {
      if (event.key === "Escape") {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("mousedown", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [isOpen]);

  return (
    <div ref={containerRef} className="relative">
      <button
        type="button"
        onClick={() => setIsOpen((open) => !open)}
        aria-haspopup="listbox"
        aria-expanded={isOpen}
        aria-label={ariaLabel}
        className={[
          "flex w-full items-center justify-between gap-2 rounded-lg border border-[#add8e6]/60 bg-white px-3 py-2 text-left text-sm transition-colors hover:border-[#add8e6] focus:border-[#add8e6] focus:outline-none focus-visible:ring-2 focus-visible:ring-[#add8e6]/50",
          className ?? "",
        ].join(" ")}
      >
        <span
          className={`truncate ${selectedOption ? "text-zinc-800" : "text-zinc-400"}`}
        >
          {selectedOption?.label ?? "選択してください"}
        </span>
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
          className="h-4 w-4 shrink-0 text-[#add8e6]"
          aria-hidden="true"
        >
          <path d="m6 9 6 6 6-6" />
        </svg>
      </button>

      {isOpen && (
        <div
          id={listboxId}
          role="listbox"
          aria-label={ariaLabel}
          className="absolute left-0 top-full z-50 mt-2 flex w-max min-w-full flex-col overflow-hidden rounded-2xl border border-line bg-white p-1 shadow-lg shadow-[#add8e6]/30"
        >
          {options.map((option) => {
            const isSelected = option.value === value;
            return (
              <button
                key={option.value}
                type="button"
                role="option"
                aria-selected={isSelected}
                onClick={() => selectOption(option.value)}
                className={[
                  "flex w-full items-center gap-2 whitespace-nowrap rounded-lg px-3 py-2 text-left text-sm transition-colors",
                  isSelected
                    ? "bg-[#add8e6] font-semibold text-sky-950"
                    : "text-zinc-700 hover:bg-[#add8e6]/20",
                ].join(" ")}
              >
                <span
                  className={isSelected ? "text-sky-950" : "text-transparent"}
                  aria-hidden="true"
                >
                  ✓
                </span>
                {option.label}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
