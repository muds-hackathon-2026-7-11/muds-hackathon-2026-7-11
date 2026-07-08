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
  // 学年(users.grade)別の志望人数(累計)。キーは "B1"〜"B4"、未設定は "不明"。
  grade_counts: Record<string, number>;
  // 志望順位(1〜3)ごとの学年別人数。キーは "1"/"2"/"3" → 学年 → 人数。
  priority_grade_counts: Record<string, Record<string, number>>;
  ratio: number | null;
  // 対象学年(#99/#103)。募集ラウンドの設定が無ければnull。
  target_grades: string[] | null;
  // 現在の所属ゼミ生数(継続者)。
  continuing_count?: number;
};

// 保存順のままだと"B2・B3・B1"のような並びになりうるため、表示前に
// 学年順へ揃える(admin-seminars-view.tsx側でも保存時に揃えているが、
// 過去に保存された順序のままのデータもあるためここでも念のため揃える)。
const GRADE_ORDER = ["B1", "B2", "B3", "B4"];

function sortByGradeOrder(targetGrades: string[]): string[] {
  return [...targetGrades].sort(
    (a, b) => GRADE_ORDER.indexOf(a) - GRADE_ORDER.indexOf(b),
  );
}

function targetGradesLabel(targetGrades: string[] | null): string {
  if (targetGrades === null) {
    return "未設定(募集していません)";
  }
  if (targetGrades.length === 0) {
    return "募集していません";
  }
  if (targetGrades.length >= GRADE_ORDER.length) {
    return "全学年";
  }
  return sortByGradeOrder(targetGrades).join("・");
}

// 学年ごとの表示色。既存UIの水色(#add8e6)に合わせた淡いパステルトーンで、
// 学年ごとに色を分ける: 1年=黄・2年=赤・3年=緑・4年=青紫。
const GRADES = [
  { key: "B1", label: "1年", color: "#f5df8e" },
  { key: "B2", label: "2年", color: "#f2a6a6" },
  { key: "B3", label: "3年", color: "#a6dcb0" },
  { key: "B4", label: "4年", color: "#b3a7e6" },
] as const;

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
        <dt>対象学年</dt>
        <dd>{targetGradesLabel(seminar.target_grades)}</dd>
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

      <p className="mt-4 text-xs font-medium text-zinc-500">
        志望者数(学年別の内訳)
      </p>
      <div className="mt-1 h-40">
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
            {GRADES.map((grade, index) => (
              <Bar
                key={grade.key}
                dataKey={grade.key}
                name={grade.label}
                stackId="grade"
                fill={grade.color}
                // 積み上げの最上段(最後の学年)だけ角丸にする。
                radius={
                  index === GRADES.length - 1 ? [4, 4, 0, 0] : [0, 0, 0, 0]
                }
              />
            ))}
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* 色分けの凡例(1年=黄・2年=赤・3年=緑・4年=青紫)。 */}
      <ul className="mt-2 flex flex-wrap gap-x-3 gap-y-1 text-xs text-zinc-600">
        {GRADES.map((grade) => (
          <li key={grade.key} className="flex items-center gap-1">
            <span
              className="inline-block h-2.5 w-2.5 rounded-sm"
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
