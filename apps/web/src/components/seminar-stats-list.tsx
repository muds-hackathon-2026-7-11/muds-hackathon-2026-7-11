"use client";

import Link from "next/link";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

export type SeminarStats = {
  id: string;
  name: string;
  capacity: number | null;
  applicant_count: number;
  priority_counts: {
    first: number;
    second: number;
    third: number;
  };
  ratio: number | null;
};

type SeminarStatsListProps = {
  stats: SeminarStats[];
};

export function SeminarStatsList({ stats }: SeminarStatsListProps) {
  if (stats.length === 0) {
    return (
      <section className="rounded-2xl border-2 border-[#add8e6] bg-white p-6 text-zinc-500 shadow-sm shadow-[#add8e6]/30">
        応募状況を取得できませんでした。
      </section>
    );
  }

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {stats.map((seminar) => (
        <SeminarStatsCard key={seminar.id} seminar={seminar} />
      ))}
    </div>
  );
}

function SeminarStatsCard({ seminar }: { seminar: SeminarStats }) {
  const chartData = [
    { label: "累計", count: seminar.applicant_count },
    { label: "第1志望", count: seminar.priority_counts.first },
    { label: "第2志望", count: seminar.priority_counts.second },
    { label: "第3志望", count: seminar.priority_counts.third },
  ];

  return (
    <section className="rounded-2xl border-2 border-[#add8e6] bg-white p-4 shadow-sm shadow-[#add8e6]/30">
      <div className="flex items-center gap-3">
        {/* ゼミアイコン用のスペース。アイコン未設定時はゼミ名の頭文字を表示。 */}
        <div className="flex h-11 w-11 shrink-0 items-center justify-center overflow-hidden rounded-full bg-[#add8e6]/20 text-lg font-bold text-sky-900">
          {seminar.name.charAt(0)}
        </div>
        <Link
          href={`/seminars/${seminar.id}`}
          className="font-semibold text-zinc-800 underline decoration-[#add8e6] underline-offset-2 hover:opacity-70"
        >
          {seminar.name}
        </Link>
      </div>

      <dl className="mt-2 grid grid-cols-2 gap-x-4 gap-y-1 text-sm text-zinc-600">
        <dt>上限人数</dt>
        <dd>{seminar.capacity ?? "未設定"}</dd>
        <dt>累計志望者数</dt>
        <dd>{seminar.applicant_count}人</dd>
        <dt>第1志望</dt>
        <dd>{seminar.priority_counts.first}人</dd>
        <dt>第2志望</dt>
        <dd>{seminar.priority_counts.second}人</dd>
        <dt>第3志望</dt>
        <dd>{seminar.priority_counts.third}人</dd>
        <dt>倍率</dt>
        <dd>{seminar.ratio ?? "-"}</dd>
      </dl>

      <div className="mt-4 h-40">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e6e6e6" />
            <XAxis
              dataKey="label"
              tick={{ fill: "#71717a", fontSize: 12 }}
              stroke="#e6e6e6"
            />
            <YAxis
              allowDecimals={false}
              tick={{ fill: "#71717a", fontSize: 12 }}
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
            <Bar dataKey="count" fill="#add8e6" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}
