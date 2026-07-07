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
      <p className="text-foreground/60">応募状況を取得できませんでした。</p>
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
    <section className="rounded-lg border border-black/[.08] p-4 dark:border-white/[.145]">
      <Link
        href={`/seminars/${seminar.id}`}
        className="font-semibold underline hover:opacity-70"
      >
        {seminar.name}
      </Link>

      <dl className="mt-2 grid grid-cols-2 gap-x-4 gap-y-1 text-sm text-foreground/70">
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
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="currentColor"
              opacity={0.15}
            />
            <XAxis
              dataKey="label"
              tick={{ fill: "currentColor", fontSize: 12 }}
              stroke="currentColor"
            />
            <YAxis
              allowDecimals={false}
              tick={{ fill: "currentColor", fontSize: 12 }}
              stroke="currentColor"
            />
            <Tooltip
              contentStyle={{
                background: "var(--background)",
                color: "var(--foreground)",
                border: "1px solid currentColor",
                fontSize: 12,
              }}
            />
            <Bar dataKey="count" fill="currentColor" />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}
