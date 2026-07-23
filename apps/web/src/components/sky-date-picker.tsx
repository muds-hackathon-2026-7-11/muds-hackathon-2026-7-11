"use client";

import { useEffect, useId, useRef, useState } from "react";

// ネイティブの<input type="date">のカレンダーはポップアップの配色を
// CSSで変更できない(ブラウザ/OS描画)。基調カラー(白/グレー/水色)に
// 揃えるため、自前のカレンダーUIを持つ日付ピッカーを用意する。
//
// 値の受け渡しはネイティブと同じ "YYYY-MM-DD" 文字列(空文字は未選択)で、
// 呼び出し側は<input type="date">とほぼ同じ感覚で使える。

const WEEKDAY_LABELS = ["日", "月", "火", "水", "木", "金", "土"] as const;
const MONTH_LABELS = [
  "1月",
  "2月",
  "3月",
  "4月",
  "5月",
  "6月",
  "7月",
  "8月",
  "9月",
  "10月",
  "11月",
  "12月",
] as const;

type YMD = { year: number; month: number; day: number };

// "YYYY-MM-DD" をパース。不正な値はnull。
function parseValue(value: string): YMD | null {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
  if (!match) {
    return null;
  }
  const year = Number(match[1]);
  const month = Number(match[2]);
  const day = Number(match[3]);
  if (month < 1 || month > 12 || day < 1 || day > 31) {
    return null;
  }
  return { year, month, day };
}

function formatValue({ year, month, day }: YMD): string {
  const mm = String(month).padStart(2, "0");
  const dd = String(day).padStart(2, "0");
  return `${year}-${mm}-${dd}`;
}

// 表示用ラベル("2027年4月1日")。未選択は空。
function formatLabel(value: string): string {
  const ymd = parseValue(value);
  if (!ymd) {
    return "";
  }
  return `${ymd.year}年${ymd.month}月${ymd.day}日`;
}

function daysInMonth(year: number, month: number): number {
  // monthは1始まり。次月の0日目 = 当月末日。
  return new Date(year, month, 0).getDate();
}

type CalendarCell = { day: number | null; key: string };

// その月のカレンダーグリッド(日曜始まり)を週単位(7の倍数)で組む。
// 前後の月の空きはday=nullで埋める。keyはindexに依存しない安定値。
function buildCalendarDays(year: number, month: number): CalendarCell[] {
  const firstWeekday = new Date(year, month - 1, 1).getDay();
  const total = daysInMonth(year, month);
  const cells: CalendarCell[] = [];
  for (let i = 0; i < firstWeekday; i++) {
    cells.push({ day: null, key: `lead-${i}` });
  }
  for (let d = 1; d <= total; d++) {
    cells.push({ day: d, key: `day-${d}` });
  }
  for (let i = 0; cells.length % 7 !== 0; i++) {
    cells.push({ day: null, key: `trail-${i}` });
  }
  return cells;
}

type SkyDatePickerProps = {
  value: string;
  onChange: (value: string) => void;
  ariaLabel?: string;
  className?: string;
};

export function SkyDatePicker({
  value,
  onChange,
  ariaLabel,
  className,
}: SkyDatePickerProps) {
  const [isOpen, setIsOpen] = useState(false);
  // カレンダーに表示中の年月。開くたびに選択値(なければ当月)へ合わせる。
  const [viewYear, setViewYear] = useState(0);
  const [viewMonth, setViewMonth] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);
  const dialogId = useId();

  const selected = parseValue(value);

  function openCalendar(): void {
    const base = selected ?? currentYMD();
    setViewYear(base.year);
    setViewMonth(base.month);
    setIsOpen(true);
  }

  function toggleCalendar(): void {
    if (isOpen) {
      setIsOpen(false);
    } else {
      openCalendar();
    }
  }

  function selectDay(day: number): void {
    onChange(formatValue({ year: viewYear, month: viewMonth, day }));
    setIsOpen(false);
  }

  function goToPreviousMonth(): void {
    setViewMonth((prevMonth) => {
      if (prevMonth === 1) {
        setViewYear((y) => y - 1);
        return 12;
      }
      return prevMonth - 1;
    });
  }

  function goToNextMonth(): void {
    setViewMonth((prevMonth) => {
      if (prevMonth === 12) {
        setViewYear((y) => y + 1);
        return 1;
      }
      return prevMonth + 1;
    });
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

  const label = formatLabel(value);
  const cells = isOpen ? buildCalendarDays(viewYear, viewMonth) : [];

  return (
    <div ref={containerRef} className="relative">
      <button
        type="button"
        onClick={toggleCalendar}
        aria-haspopup="dialog"
        aria-expanded={isOpen}
        aria-label={ariaLabel}
        className={[
          "flex w-full items-center justify-between gap-2 rounded-lg border border-line bg-white px-3 py-2 text-left text-sm transition-colors hover:border-[#add8e6] focus:border-[#add8e6] focus:outline-none focus-visible:ring-2 focus-visible:ring-[#add8e6]/50",
          className ?? "",
        ].join(" ")}
      >
        <span className={label ? "text-zinc-800" : "text-zinc-400"}>
          {label || "日付を選択"}
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
          <rect x="3" y="4" width="18" height="18" rx="2" />
          <path d="M16 2v4M8 2v4M3 10h18" />
        </svg>
      </button>

      {isOpen && (
        <div
          id={dialogId}
          role="dialog"
          aria-label={ariaLabel ?? "カレンダー"}
          className="absolute left-0 top-full z-50 mt-2 w-72 rounded-2xl border border-line bg-white p-3 shadow-lg shadow-[#add8e6]/30"
        >
          <div className="flex items-center justify-between">
            <button
              type="button"
              onClick={goToPreviousMonth}
              aria-label="前の月"
              className="flex h-7 w-7 items-center justify-center rounded-full text-zinc-500 transition-colors hover:bg-[#add8e6]/10 hover:text-zinc-800"
            >
              ‹
            </button>
            <p className="text-sm font-semibold text-zinc-800">
              {viewYear}年 {MONTH_LABELS[viewMonth - 1]}
            </p>
            <button
              type="button"
              onClick={goToNextMonth}
              aria-label="次の月"
              className="flex h-7 w-7 items-center justify-center rounded-full text-zinc-500 transition-colors hover:bg-[#add8e6]/10 hover:text-zinc-800"
            >
              ›
            </button>
          </div>

          <div className="mt-2 grid grid-cols-7 gap-0.5">
            {WEEKDAY_LABELS.map((weekday) => (
              <div
                key={weekday}
                className="flex h-7 items-center justify-center text-xs font-medium text-zinc-400"
              >
                {weekday}
              </div>
            ))}
            {cells.map((cell) => {
              if (cell.day === null) {
                return <div key={cell.key} className="h-8" />;
              }
              const day = cell.day;
              const isSelected =
                selected !== null &&
                selected.year === viewYear &&
                selected.month === viewMonth &&
                selected.day === day;
              return (
                <button
                  key={cell.key}
                  type="button"
                  onClick={() => selectDay(day)}
                  aria-pressed={isSelected}
                  className={[
                    "flex h-8 items-center justify-center rounded-lg text-sm transition-colors",
                    isSelected
                      ? "bg-[#add8e6] font-semibold text-sky-950"
                      : "text-zinc-700 hover:bg-[#add8e6]/20",
                  ].join(" ")}
                >
                  {day}
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

// 今日の年月日。SSRとクライアントでずれ得るため、開く操作(クライアント)
// でのみ呼ぶ。
function currentYMD(): YMD {
  const now = new Date();
  return {
    year: now.getFullYear(),
    month: now.getMonth() + 1,
    day: now.getDate(),
  };
}
