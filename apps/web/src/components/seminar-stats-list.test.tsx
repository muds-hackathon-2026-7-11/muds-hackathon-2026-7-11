import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { SeminarStatsList, type SeminarStats } from "./seminar-stats-list";

const stats: SeminarStats[] = [
  {
    id: "seminar-1",
    name: "AIゼミ",
    capacity: 10,
    applicant_count: 5,
    priority_counts: { first: 2, second: 2, third: 1 },
    grade_counts: { B1: 1, B2: 1, B3: 2, B4: 1 },
    priority_grade_counts: {
      "1": { B3: 1, B4: 1 },
      "2": { B1: 1, B3: 1 },
      "3": { B2: 1 },
    },
    ratio: 0.5,
    target_grades: ["B1", "B2", "B3", "B4"],
    continuing_first_choice_count: 2,
  },
  {
    id: "seminar-2",
    name: "Webゼミ",
    capacity: null,
    applicant_count: 0,
    priority_counts: { first: 0, second: 0, third: 0 },
    grade_counts: {},
    priority_grade_counts: { "1": {}, "2": {}, "3": {} },
    ratio: null,
    target_grades: null,
    continuing_first_choice_count: 0,
  },
];

describe("SeminarStatsList", () => {
  it("renders a card per seminar with its stats", () => {
    render(<SeminarStatsList stats={stats} />);

    expect(screen.getByText("AIゼミ")).toBeInTheDocument();
    expect(screen.getByText("Webゼミ")).toBeInTheDocument();
    expect(screen.getByText("10人")).toBeInTheDocument();

    const labels = screen.getAllByText("第1志望");
    expect(labels[0].nextElementSibling).toHaveTextContent("2人");
    expect(labels[1].nextElementSibling).toHaveTextContent("0人");
  });

  it("falls back to a placeholder for missing capacity", () => {
    render(<SeminarStatsList stats={stats} />);

    expect(screen.getAllByText("未設定")).toHaveLength(1);
  });

  it("links each seminar name to its detail page", () => {
    render(<SeminarStatsList stats={stats} />);

    expect(screen.getByRole("link", { name: "AIゼミ" })).toHaveAttribute(
      "href",
      "/seminars/seminar-1",
    );
    expect(screen.getByRole("link", { name: "Webゼミ" })).toHaveAttribute(
      "href",
      "/seminars/seminar-2",
    );
  });

  it("shows a per-grade legend (1年〜4年) on each card", () => {
    render(<SeminarStatsList stats={stats} />);

    // 2ゼミ分 × 学年ラベル(凡例 + X軸)。少なくとも各学年が描画される。
    for (const label of ["1年", "2年", "3年", "4年"]) {
      expect(screen.getAllByText(label).length).toBeGreaterThan(0);
    }
  });

  it("shows the continuing first-choice count for each seminar", () => {
    render(<SeminarStatsList stats={stats} />);

    const labels = screen.getAllByText("継続希望人数");
    expect(labels[0].nextElementSibling).toHaveTextContent("2人");
    expect(labels[1].nextElementSibling).toHaveTextContent("0人");
  });

  it("shows a message when there are no stats", () => {
    render(<SeminarStatsList stats={[]} />);

    expect(
      screen.getByText("応募状況を取得できませんでした。"),
    ).toBeInTheDocument();
  });
});
