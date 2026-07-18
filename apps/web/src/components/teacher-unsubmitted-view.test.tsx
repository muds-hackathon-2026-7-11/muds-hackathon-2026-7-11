import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import {
  TeacherUnsubmittedView,
  type UnsubmittedApplicant,
} from "./teacher-unsubmitted-view";

function makeApplicants(): UnsubmittedApplicant[] {
  return [
    { student_id: "s2322087", name: "橘 由翔", grade: "B4" },
    { student_id: "s2422108", name: "阪田 琴美", grade: "B3" },
    // 実データの表記揺れ(#99)。バックエンドはnormalize_gradeで末尾一致
    // 判定するため、フロントのフィルタも同じ判定をしないと「B3」を
    // 押しても消えてしまう(#182で見つかったバグの回帰テスト)。
    { student_id: null, name: "MIDS学生", grade: "MIDS/B3" },
    { student_id: "s2522001", name: "学年不明太郎", grade: null },
  ];
}

describe("TeacherUnsubmittedView", () => {
  it("renders every unsubmitted applicant with grade and student id", () => {
    render(<TeacherUnsubmittedView applicants={makeApplicants()} />);

    expect(screen.getByText("橘 由翔")).toBeInTheDocument();
    expect(screen.getByText("s2322087")).toBeInTheDocument();
    expect(screen.getByText("学年不明太郎")).toBeInTheDocument();
    expect(screen.getByText("学年不明")).toBeInTheDocument();
    expect(screen.getByText("4名 / 全4名 未提出")).toBeInTheDocument();
  });

  it("shows a message when there are no unsubmitted applicants", () => {
    render(<TeacherUnsubmittedView applicants={[]} />);

    expect(screen.getByText("未提出の学生はいません。")).toBeInTheDocument();
  });

  it("filters by grade using the same suffix-match rule as the backend", async () => {
    const user = userEvent.setup();
    render(<TeacherUnsubmittedView applicants={makeApplicants()} />);

    await user.click(screen.getByRole("button", { name: "B3" }));

    // 表記が "B3" そのままの学生と "MIDS/B3" の学生の両方が残る。
    expect(screen.getByText("阪田 琴美")).toBeInTheDocument();
    expect(screen.getByText("MIDS学生")).toBeInTheDocument();
    expect(screen.queryByText("橘 由翔")).not.toBeInTheDocument();
    expect(screen.queryByText("学年不明太郎")).not.toBeInTheDocument();
    expect(screen.getByText("2名 / 全4名 未提出")).toBeInTheDocument();
  });
});
