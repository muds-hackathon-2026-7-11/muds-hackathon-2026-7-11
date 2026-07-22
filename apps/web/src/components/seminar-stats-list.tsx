"use client";

import Link from "next/link";
import { useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  usePlotArea,
  useXAxisScale,
  XAxis,
  YAxis,
} from "recharts";

export type SeminarStats = {
  id: string;
  name: string;
  capacity: number | null;
  // アイコン表示用(#139)。ゼミ自体の写真を最優先で使う。
  photo_url: string | null;
  // アイコン表示用(#139)。担当教員が1人だけの場合のみ、その教員の写真を
  // ゼミ写真未設定時のフォールバックとして使う(複数教員なら常にnull)。
  teacher_photo_url: string | null;
  applicant_count: number;
  priority_counts: {
    first: number;
    second: number;
    third: number;
  };
  // 学年(users.grade)別の志望人数(累計)。キーは "B1"〜"B4"、未設定は "不明"。
  grade_counts: Record<string, number>;
  // 志望順位(1〜3)ごとの学年別人数。キーは "1"/"2"/"3" → 学年 → 人数。
  priority_grade_counts: Record<string, Record<string, number>>;
  ratio: number | null;
  // 対象学年(#99/#103)。募集ラウンドの設定が無ければnull。
  target_grades: string[] | null;
  // 現在の所属ゼミ生数(継続者)。
  continuing_count?: number;
  // 継続希望人数: 在籍ゼミ生のうち、同じゼミを第1志望に選んだ人数。
  continuing_first_choice_count: number;
};

// 学年ごとの表示色。既存UIの水色(#add8e6)に合わせた淡いパステルトーンで、
// 学年ごとに色を分ける: 1年=黄・2年=赤・3年=緑・4年=青紫。
const GRADES = [
  { key: "B1", label: "1年", color: "#f5df8e" },
  { key: "B2", label: "2年", color: "#f2a6a6" },
  { key: "B3", label: "3年", color: "#a6dcb0" },
  { key: "B4", label: "4年", color: "#b3a7e6" },
] as const;

type ChartTooltipEntry = {
  dataKey?: string;
  name?: string;
  value?: number;
  color?: string;
};

function StatsTooltip({
  active,
  label,
  payload,
}: {
  active?: boolean;
  label?: string;
  payload?: ChartTooltipEntry[];
}) {
  if (!active || !payload || payload.length === 0) {
    return null;
  }
  const total = payload.reduce((sum, entry) => sum + (entry.value ?? 0), 0);
  return (
    <div className="rounded-lg border border-[#add8e6] bg-white px-3 py-2 text-sm shadow">
      <p className="font-semibold text-zinc-800">
        {label}: {total}人
      </p>
      {payload.map((entry) => (
        <p
          key={entry.dataKey}
          className="flex items-center gap-1.5 text-zinc-700"
        >
          <span
            className="inline-block h-2.5 w-2.5 shrink-0 rounded-sm"
            style={{ backgroundColor: entry.color }}
            aria-hidden
          />
          {entry.name}: {entry.value ?? 0}人
        </p>
      ))}
    </div>
  );
}

// 各バー(カテゴリ)の境目に点線を引く。CartesianGridの縦線はバーの
// 中心(目盛りの位置)を通ってしまうため、バンドスケールの右端を
// 明示的に取得して境界線として描画する(Recharts 3のuseXAxisScale/
// usePlotAreaはCustomized無しでチャート内に直接置いて使える)。
function CategoryDividers({ categories }: { categories: string[] }) {
  const xScale = useXAxisScale();
  const plotArea = usePlotArea();
  if (!xScale || !plotArea) {
    return null;
  }
  const innerBoundaries = categories
    .slice(0, -1)
    .map((category) => xScale(category, { position: "end" }))
    .filter((x): x is number => x !== undefined);
  // プロット領域の左端・右端(両端のバーの外側)にも枠線を引く。
  const boundaries = [
    plotArea.x,
    ...innerBoundaries,
    plotArea.x + plotArea.width,
  ];

  return (
    <>
      {boundaries.map((x) => (
        <line
          key={x}
          x1={x}
          x2={x}
          y1={plotArea.y}
          y2={plotArea.y + plotArea.height}
          stroke="#d4d4d8"
          strokeDasharray="3 3"
        />
      ))}
    </>
  );
}

// ゼミアイコン。ゼミ自体の写真があればそれを優先し、無ければ(担当教員が
// 1人だけの場合に限り)その教員の写真、どちらも無ければ頭文字を表示する
// (seminar-detail.tsxのTeacherAvatarと同じ優先順位、#139)。
function SeminarAvatar({ seminar }: { seminar: SeminarStats }) {
  const src = seminar.photo_url ?? seminar.teacher_photo_url;
  const [erroredSrc, setErroredSrc] = useState<string | null>(null);

  if (src && src !== erroredSrc) {
    return (
      // biome-ignore lint/performance/noImgElement: photo_urlは任意の外部ドメインのため next/image のドメイン許可設定が不要なimgタグを使う
      <img
        src={src}
        alt={seminar.name}
        onError={() => setErroredSrc(src)}
        className="h-20 w-20 shrink-0 rounded-full object-cover"
      />
    );
  }
  return (
    <div className="flex h-20 w-20 shrink-0 items-center justify-center overflow-hidden rounded-full bg-[#add8e6]/20 text-3xl font-bold text-sky-900">
      {seminar.name.charAt(0)}
    </div>
  );
}

type SeminarStatsListProps = {
  stats: SeminarStats[];
};

export function SeminarStatsList({ stats }: SeminarStatsListProps) {
  if (stats.length === 0) {
    return (
      <section className="rounded-2xl border border-line bg-white p-6 text-zinc-500 shadow-sm shadow-[#add8e6]/30">
        応募状況を取得できませんでした。
      </section>
    );
  }

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-2 xl:grid-cols-3">
      {stats.map((seminar) => (
        <SeminarStatsCard key={seminar.id} seminar={seminar} />
      ))}
    </div>
  );
}

function SeminarStatsCard({ seminar }: { seminar: SeminarStats }) {
  // 横軸は 累計/第1〜第3志望。各棒はその人数を学年で積み上げて色分けする。
  const categories: { label: string; counts: Record<string, number> }[] = [
    { label: "累計", counts: seminar.grade_counts ?? {} },
    { label: "第1志望", counts: seminar.priority_grade_counts?.["1"] ?? {} },
    { label: "第2志望", counts: seminar.priority_grade_counts?.["2"] ?? {} },
    { label: "第3志望", counts: seminar.priority_grade_counts?.["3"] ?? {} },
  ];
  const chartData = categories.map((category) => {
    const row: { label: string } & Record<string, number | string> = {
      label: category.label,
    };
    for (const grade of GRADES) {
      row[grade.key] = category.counts[grade.key] ?? 0;
    }
    return row;
  });
  const categoryLabels = categories.map((category) => category.label);
  // 縦軸の最大値: 累計志望者数を5の倍数へ繰り上げる(最低5)。
  const yAxisMax = Math.max(5, Math.ceil(seminar.applicant_count / 5) * 5);
  // 目盛りは0,5,10,...を明示し、recharts任せの自動目盛り(2や4等)を防ぐ。
  const yAxisTicks = Array.from({ length: yAxisMax / 5 + 1 }, (_, i) => i * 5);

  return (
    <section className="rounded-2xl border border-line bg-white p-6 shadow-sm shadow-[#add8e6]/30">
      <div className="flex items-center gap-4">
        <SeminarAvatar seminar={seminar} />
        <Link
          href={`/seminars/${seminar.id}`}
          className="text-lg font-semibold text-zinc-800 underline decoration-[#add8e6] underline-offset-2 hover:opacity-70"
        >
          {seminar.name}
        </Link>
      </div>

      <dl className="mt-4 ml-2 grid grid-cols-2 gap-x-4 gap-y-3 text-zinc-600 sm:grid-cols-3">
        <div>
          <dt className="text-xs text-zinc-600">上限人数</dt>
          <dd className="text-base font-medium text-zinc-900">
            {seminar.capacity != null ? `${seminar.capacity}人` : "未設定"}
          </dd>
        </div>
        <div>
          <dt className="text-xs text-zinc-600">第1志望</dt>
          <dd className="text-base font-medium text-zinc-900">
            {seminar.priority_counts.first}人
          </dd>
        </div>
        <div>
          <dt className="text-xs text-zinc-600">継続希望人数</dt>
          <dd className="text-base font-medium text-zinc-900">
            {seminar.continuing_first_choice_count}人
          </dd>
        </div>
      </dl>

      <div className="mt-4 h-52">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={chartData}
            margin={{ top: 4, right: 8, bottom: 0, left: 0 }}
            // バーの太さ(帯のうち隙間にしない割合)。値が小さいほど太くなる。
            barCategoryGap="25%"
          >
            <CartesianGrid
              vertical={false}
              strokeDasharray="3 3"
              stroke="#e6e6e6"
            />
            <CategoryDividers categories={categoryLabels} />
            <XAxis
              dataKey="label"
              tick={{ fill: "#71717a", fontSize: 13 }}
              stroke="#e6e6e6"
            />
            <YAxis
              allowDecimals={false}
              width={28}
              domain={[0, yAxisMax]}
              ticks={yAxisTicks}
              tick={{ fill: "#71717a", fontSize: 13 }}
              stroke="#e6e6e6"
            />
            <Tooltip
              cursor={{ fill: "#3f3f46", opacity: 0.15 }}
              content={<StatsTooltip />}
            />
            {GRADES.map((grade) => (
              <Bar
                key={grade.key}
                dataKey={grade.key}
                name={grade.label}
                stackId="grade"
                fill={grade.color}
              />
            ))}
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* 色分けの凡例(1年=黄・2年=赤・3年=緑・4年=青紫)。 */}
      <ul className="mt-3 ml-2 flex flex-wrap gap-x-4 gap-y-1 text-sm text-zinc-600">
        {GRADES.map((grade) => (
          <li key={grade.key} className="flex items-center gap-1.5">
            <span
              className="inline-block h-3 w-3 rounded-sm"
              style={{ backgroundColor: grade.color }}
              aria-hidden
            />
            {grade.label}
          </li>
        ))}
      </ul>
    </section>
  );
}
