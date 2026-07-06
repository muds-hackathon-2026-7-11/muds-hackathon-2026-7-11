import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ProfileCard } from "./profile-card";

describe("ProfileCard", () => {
  it("renders the name, email, grade, and research theme", () => {
    render(
      <ProfileCard
        name="山田 太郎"
        email="s2300000@stu.musashino-u.ac.jp"
        grade="B3"
        researchTheme="音声処理の研究"
      />,
    );

    expect(screen.getByText("山田 太郎")).toBeInTheDocument();
    expect(
      screen.getByText("s2300000@stu.musashino-u.ac.jp"),
    ).toBeInTheDocument();
    expect(screen.getByText("B3")).toBeInTheDocument();
    expect(screen.getByText("音声処理の研究")).toBeInTheDocument();
  });

  it("keeps a different faculty's grade string as-is (e.g. MIDS)", () => {
    render(
      <ProfileCard
        name="佐藤 花子"
        email="s2300001@stu.musashino-u.ac.jp"
        grade="MIDS/B1"
        researchTheme={null}
      />,
    );

    expect(screen.getByText("MIDS/B1")).toBeInTheDocument();
  });

  it("falls back to a placeholder when grade or researchTheme is missing", () => {
    render(
      <ProfileCard
        name="山田 太郎"
        email="s2300000@stu.musashino-u.ac.jp"
        grade={null}
        researchTheme={null}
      />,
    );

    expect(screen.getAllByText("未設定")).toHaveLength(2);
  });

  it("renders the edit button as disabled", () => {
    render(
      <ProfileCard
        name="山田 太郎"
        email="s2300000@stu.musashino-u.ac.jp"
        grade={null}
        researchTheme={null}
      />,
    );

    expect(screen.getByRole("button", { name: "編集" })).toBeDisabled();
  });
});
