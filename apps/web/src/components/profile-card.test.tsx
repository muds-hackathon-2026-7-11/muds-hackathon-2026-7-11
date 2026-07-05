import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ProfileCard } from "./profile-card";

describe("ProfileCard", () => {
  it("renders the name, joined meta line, and research theme", () => {
    render(
      <ProfileCard
        name="山田 太郎"
        studentId="s2300000"
        grade="B3"
        researchTheme="音声処理の研究"
      />,
    );

    expect(screen.getByText("山田 太郎")).toBeInTheDocument();
    expect(screen.getByText("s2300000・B3")).toBeInTheDocument();
    expect(screen.getByText("音声処理の研究")).toBeInTheDocument();
  });

  it("keeps a different faculty's grade string as-is (e.g. MIDS)", () => {
    render(
      <ProfileCard
        name="佐藤 花子"
        studentId="s2300001"
        grade="MIDS/B1"
        researchTheme={null}
      />,
    );

    expect(screen.getByText("s2300001・MIDS/B1")).toBeInTheDocument();
  });

  it("falls back to a placeholder when researchTheme is missing", () => {
    render(
      <ProfileCard
        name="山田 太郎"
        studentId={null}
        grade={null}
        researchTheme={null}
      />,
    );

    expect(screen.getByText("未設定")).toBeInTheDocument();
  });

  it("renders the edit button as disabled", () => {
    render(
      <ProfileCard
        name="山田 太郎"
        studentId={null}
        grade={null}
        researchTheme={null}
      />,
    );

    expect(screen.getByRole("button", { name: "編集" })).toBeDisabled();
  });
});
