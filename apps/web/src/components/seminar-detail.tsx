"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

type ResearchTag = {
  id: string;
  name: string;
  category: string;
};

type Teacher = {
  id: string;
  name: string;
  photo_url: string | null;
  interest_tags: ResearchTag[];
};

type Material = {
  id: string;
  url: string;
  type: "slide" | "pdf" | "video";
};

type Member = {
  id: string;
  name: string;
  grade: string | null;
  research_title: string | null;
  research_theme: string | null;
  interest_tags: ResearchTag[];
};

export type SeminarDetail = {
  id: string;
  name: string;
  description: string | null;
  photo_url: string | null;
  teachers: Teacher[];
  materials: Material[];
  current_members: Member[];
};

const MATERIAL_TYPE_LABEL: Record<Material["type"], string> = {
  slide: "スライド",
  pdf: "PDF",
  video: "動画",
};

function TeacherAvatar({
  name,
  photoUrl,
  seminarPhotoUrl,
}: {
  name: string;
  photoUrl: string | null;
  seminarPhotoUrl: string | null;
}) {
  // ゼミの研究室写真があればそちらを優先し、無ければ教員本人の写真、
  // それも無ければ頭文字にフォールバックする。
  const src = seminarPhotoUrl ?? photoUrl;
  const [erroredSrc, setErroredSrc] = useState<string | null>(null);

  if (src && src !== erroredSrc) {
    return (
      // biome-ignore lint/performance/noImgElement: photo_urlは任意の外部ドメインのため next/image のドメイン許可設定が不要なimgタグを使う
      <img
        src={src}
        alt={name}
        onError={() => setErroredSrc(src)}
        className="h-20 w-20 shrink-0 rounded-full object-cover"
      />
    );
  }
  return (
    <div className="flex h-20 w-20 shrink-0 items-center justify-center rounded-full bg-[#add8e6]/20 text-2xl font-bold text-sky-900">
      {Array.from(name)[0] ?? "?"}
    </div>
  );
}

// Y軸のタグ名が長いと省略されずにはみ出す/隣と重なるため、一定の文字数で
// 省略記号を付けて切り、ホバー時はSVGのtitleで全文を見せる。
function TruncatedYAxisTick({
  x,
  y,
  payload,
}: {
  x?: number;
  y?: number;
  payload?: { value: string };
}) {
  const value = payload?.value ?? "";
  const truncated = value.length > 10 ? `${value.slice(0, 9)}…` : value;
  return (
    <text x={x} y={y} dy={4} textAnchor="end" fontSize={12} fill="#71717a">
      <title>{value}</title>
      {truncated}
    </text>
  );
}

function tagChartData(members: Member[]): { name: string; count: number }[] {
  const counts = new Map<string, number>();
  for (const member of members) {
    for (const tag of member.interest_tags) {
      counts.set(tag.name, (counts.get(tag.name) ?? 0) + 1);
    }
  }
  return Array.from(counts.entries())
    .map(([name, count]) => ({ name, count }))
    .sort((a, b) => b.count - a.count);
}

// タグ名 -> そのタグを持つゼミ生の名前一覧。グラフのバーをクリックした時に
// 「誰がその分野をやっているか」を表示するために使う。
function membersByTag(members: Member[]): Map<string, string[]> {
  const map = new Map<string, string[]>();
  for (const member of members) {
    for (const tag of member.interest_tags) {
      const names = map.get(tag.name) ?? [];
      names.push(member.name);
      map.set(tag.name, names);
    }
  }
  return map;
}

type SeminarDetailViewProps = {
  seminar: SeminarDetail;
};

export function SeminarDetailView({ seminar }: SeminarDetailViewProps) {
  const chartData = useMemo(
    () => tagChartData(seminar.current_members),
    [seminar.current_members],
  );
  // クリックで研究概要モーダルを開いているゼミ生のid。
  const [openMemberId, setOpenMemberId] = useState<string | null>(null);
  const openMember =
    seminar.current_members.find((m) => m.id === openMemberId) ?? null;

  // グラフのバーをクリックした時に開く「その分野をやっているゼミ生」モーダル。
  const membersByTagMap = useMemo(
    () => membersByTag(seminar.current_members),
    [seminar.current_members],
  );
  const [openTag, setOpenTag] = useState<string | null>(null);
  const openTagMembers = openTag ? (membersByTagMap.get(openTag) ?? []) : [];

  return (
    <div className="flex flex-col gap-6">
      <Link
        href="/assignment"
        className="self-start text-sm text-zinc-900 underline decoration-[#add8e6] underline-offset-2 hover:opacity-70"
      >
        ← 応募状況に戻る
      </Link>

      {/* ゼミ名は枠外に大きく表示し、その横にFAQボタンを置く。 */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h1 className="border-l-4 border-[#add8e6] pl-3 text-3xl font-bold text-zinc-900">
          {seminar.name}
        </h1>
        <Link
          href={`/seminars/${seminar.id}/questions`}
          className="shrink-0 rounded-full bg-[#add8e6] px-5 py-2 text-sm font-semibold text-sky-950 shadow-sm transition-all hover:bg-[#9bcfe0] hover:shadow active:translate-y-px focus:outline-none focus-visible:ring-4 focus-visible:ring-[#add8e6]/50"
        >
          FAQ
        </Link>
      </div>

      <section className="rounded-2xl border-2 border-[#add8e6] bg-white p-6 shadow-sm shadow-[#add8e6]/30">
        <h2 className="text-lg font-bold text-zinc-900">教員紹介</h2>
        {seminar.teachers.length === 0 ? (
          <p className="mt-2 text-sm text-zinc-900">未設定です。</p>
        ) : (
          <div className="mt-3 flex flex-wrap gap-6">
            {seminar.teachers.map((teacher) => (
              <div
                key={teacher.id}
                className="flex min-w-[240px] flex-1 items-center gap-4"
              >
                <TeacherAvatar
                  name={teacher.name}
                  photoUrl={teacher.photo_url}
                  seminarPhotoUrl={seminar.photo_url}
                />
                <div className="min-w-0">
                  <p className="font-semibold text-zinc-900">{teacher.name}</p>
                  {teacher.interest_tags.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-2">
                      {teacher.interest_tags.map((tag) => (
                        <span
                          key={tag.id}
                          className="rounded-full border border-[#add8e6]/60 bg-[#add8e6]/10 px-3 py-1 text-xs text-zinc-900"
                        >
                          {tag.name}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      <section className="rounded-2xl border-2 border-[#add8e6] bg-white p-6 shadow-sm shadow-[#add8e6]/30">
        <h2 className="text-lg font-bold text-zinc-900">研究内容</h2>
        {seminar.description && (
          <p className="mt-2 whitespace-pre-wrap text-zinc-900">
            {seminar.description}
          </p>
        )}

        {seminar.materials.length === 0 ? (
          <p className="mt-2 text-sm text-zinc-900">資料はまだありません。</p>
        ) : (
          <ul className="mt-2 flex flex-col gap-1">
            {seminar.materials.map((material) => (
              <li
                key={material.id}
                className="flex min-w-0 items-baseline gap-2"
              >
                <span className="shrink-0 text-xs text-zinc-400">
                  {MATERIAL_TYPE_LABEL[material.type]}
                </span>
                <a
                  href={material.url}
                  target="_blank"
                  rel="noreferrer"
                  className="min-w-0 truncate text-sm text-zinc-900 underline decoration-[#add8e6] underline-offset-2 hover:opacity-70"
                >
                  {material.url}
                </a>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="rounded-2xl border-2 border-[#add8e6] bg-white p-6 shadow-sm shadow-[#add8e6]/30">
        <h2 className="text-lg font-bold text-zinc-900">
          現在のゼミ生の研究分野
        </h2>
        {chartData.length === 0 ? (
          <p className="mt-2 text-sm text-zinc-900">
            集計できるデータがありません。
          </p>
        ) : (
          <div
            className="mt-4"
            style={{ height: Math.max(256, chartData.length * 32) }}
          >
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="#e6e6e6" />
                <XAxis
                  type="number"
                  allowDecimals={false}
                  tick={{ fill: "#71717a", fontSize: 12 }}
                  stroke="#e6e6e6"
                />
                <YAxis
                  type="category"
                  dataKey="name"
                  width={100}
                  tick={<TruncatedYAxisTick />}
                  stroke="#e6e6e6"
                />
                <Tooltip
                  cursor={{ fill: "#add8e6", opacity: 0.15 }}
                  contentStyle={{
                    background: "#ffffff",
                    color: "#3f3f46",
                    border: "1px solid #add8e6",
                    borderRadius: 8,
                    fontSize: 12,
                  }}
                />
                <Bar
                  dataKey="count"
                  fill="#add8e6"
                  radius={[0, 4, 4, 0]}
                  cursor="pointer"
                  onClick={(data: { name?: string }) => {
                    if (data?.name) {
                      setOpenTag(data.name);
                    }
                  }}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </section>

      <section className="rounded-2xl border-2 border-[#add8e6] bg-white p-6 shadow-sm shadow-[#add8e6]/30">
        <h2 className="text-lg font-bold text-zinc-900">現在のゼミ生</h2>
        {seminar.current_members.length === 0 ? (
          <p className="mt-2 text-sm text-zinc-900">未設定です。</p>
        ) : (
          <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-3">
            {seminar.current_members.map((member) => (
              <button
                key={member.id}
                type="button"
                onClick={() => setOpenMemberId(member.id)}
                className="rounded-xl border border-[#add8e6]/50 px-3 py-2 text-left transition-colors hover:bg-[#add8e6]/10"
              >
                <span className="block truncate font-semibold text-zinc-900">
                  {member.grade
                    ? `${member.grade} ${member.name}`
                    : member.name}
                </span>
                {/* 研究タイトルは研究概要(research_theme)とは別項目。
                    詳しい研究概要・タグは名前クリックのモーダルで見せる。 */}
                <span className="mt-0.5 block truncate text-xs text-zinc-900">
                  {member.research_title ?? "研究タイトル未設定"}
                </span>
              </button>
            ))}
          </div>
        )}
      </section>

      {openMember && (
        // biome-ignore lint/a11y/noStaticElementInteractions: 背景クリックで閉じるための領域(キーボードはEscで代替)
        // biome-ignore lint/a11y/useKeyWithClickEvents: Escキーはブラウザ既定のダイアログ挙動ではなく、閉じるボタンで代替する
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
          onClick={(e) => {
            if (e.target === e.currentTarget) {
              setOpenMemberId(null);
            }
          }}
        >
          <div
            role="dialog"
            aria-modal="true"
            aria-label={`${openMember.name}の研究概要`}
            className="w-full max-w-2xl rounded-2xl border-2 border-[#add8e6] bg-white p-8 shadow-lg shadow-[#add8e6]/30"
          >
            <div className="flex items-start justify-between gap-4">
              <div className="min-w-0">
                <p className="text-base font-medium text-zinc-900">
                  {openMember.grade
                    ? `${openMember.grade} ${openMember.name}`
                    : openMember.name}
                </p>
                <p className="mt-1 text-xl font-bold text-zinc-900">
                  {openMember.research_title ?? "研究タイトル未設定"}
                </p>
              </div>
              <button
                type="button"
                onClick={() => setOpenMemberId(null)}
                aria-label="閉じる"
                className="shrink-0 rounded-full p-1 text-zinc-400 transition-colors hover:bg-[#e6e6e6]/60 hover:text-zinc-700"
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
                  <path d="M18 6 6 18M6 6l12 12" />
                </svg>
              </button>
            </div>

            <p className="mt-4 text-xs font-semibold uppercase tracking-wider text-zinc-900">
              研究概要
            </p>
            <p className="mt-1 whitespace-pre-wrap text-zinc-900">
              {openMember.research_theme ?? "未設定"}
            </p>

            {openMember.interest_tags.length > 0 && (
              <div className="mt-4 flex flex-wrap gap-2">
                {openMember.interest_tags.map((tag) => (
                  <span
                    key={tag.id}
                    className="rounded-full border border-[#add8e6]/60 bg-[#add8e6]/10 px-3 py-1 text-xs text-zinc-900"
                  >
                    {tag.name}
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {openTag && (
        // biome-ignore lint/a11y/noStaticElementInteractions: 背景クリックで閉じるための領域
        // biome-ignore lint/a11y/useKeyWithClickEvents: 閉じるボタンで代替する
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
          onClick={(e) => {
            if (e.target === e.currentTarget) {
              setOpenTag(null);
            }
          }}
        >
          <div
            role="dialog"
            aria-modal="true"
            aria-label={`${openTag}の研究をしているゼミ生`}
            className="w-full max-w-lg rounded-2xl border-2 border-[#add8e6] bg-white p-6 shadow-lg shadow-[#add8e6]/30"
          >
            <div className="flex items-start justify-between gap-4">
              <p className="text-xl font-bold text-zinc-900">{openTag}</p>
              <button
                type="button"
                onClick={() => setOpenTag(null)}
                aria-label="閉じる"
                className="shrink-0 rounded-full p-1 text-zinc-400 transition-colors hover:bg-[#e6e6e6]/60 hover:text-zinc-700"
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
                  <path d="M18 6 6 18M6 6l12 12" />
                </svg>
              </button>
            </div>

            <p className="mt-4 text-xs font-semibold uppercase tracking-wider text-zinc-900">
              この分野のゼミ生 ({openTagMembers.length}人)
            </p>
            <ul className="mt-2 flex flex-wrap gap-2">
              {openTagMembers.map((name) => (
                <li
                  key={name}
                  className="rounded-full border border-[#add8e6]/60 bg-[#add8e6]/10 px-3 py-1 text-sm text-zinc-900"
                >
                  {name}
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}
