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
    ratio: 0.5,
  },
  {
    id: "seminar-2",
    name: "Webゼミ",
    capacity: null,
    applicant_count: 0,
    priority_counts: { first: 0, second: 0, third: 0 },
    ratio: null,
  },
];

describe("SeminarStatsList", () => {
  it("renders a card per seminar with its stats", () => {
    render(<SeminarStatsList stats={stats} />);

    expect(screen.getByText("AIゼミ")).toBeInTheDocument();
    expect(screen.getByText("Webゼミ")).toBeInTheDocument();
    expect(screen.getByText("5人")).toBeInTheDocument();
    expect(screen.getByText("10")).toBeInTheDocument();
  });

  it("falls back to placeholders for missing capacity and ratio", () => {
    render(<SeminarStatsList stats={stats} />);

    expect(screen.getAllByText("未設定")).toHaveLength(1);
    expect(screen.getAllByText("-")).toHaveLength(1);
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

  it("shows a message when there are no stats", () => {
    render(<SeminarStatsList stats={[]} />);

    expect(
      screen.getByText("応募状況を取得できませんでした。"),
    ).toBeInTheDocument();
  });
});
