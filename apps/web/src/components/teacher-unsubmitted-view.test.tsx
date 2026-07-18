import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import {
  TeacherUnsubmittedView,
  type UnsubmittedApplicant,
} from "./teacher-unsubmitted-view";

function makeApplicants(): UnsubmittedApplicant[] {
  return [
    {
      student_id: "s2322087",
      name: "橘 由翔",
      grade: "B4",
      normalized_grade: "B4",
    },
    {
      student_id: "s2422108",
      name: "阪田 琴美",
      grade: "B3",
      normalized_grade: "B3",
    },
    // 実データの表記揺れ(#99)。表示は生のgrade("MIDS/B3")のままだが、
    // フィルタ判定はAPI側で正規化済みのnormalized_gradeを使う(#182で
    // 見つかった、フロント側で正規化ルールを再実装して食い違わせるバグの
    // 回帰テスト)。
    {
      student_id: null,
      name: "MIDS学生",
      grade: "MIDS/B3",
      normalized_grade: "B3",
    },
    {
      student_id: "s2522001",
      name: "学年不明太郎",
      grade: null,
      normalized_grade: null,
    },
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

  it("filters by grade using the API's normalized_grade", async () => {
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
