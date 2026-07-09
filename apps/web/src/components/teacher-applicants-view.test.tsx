import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useSession } from "next-auth/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import {
  TeacherApplicantsView,
  type SeminarApplicants,
} from "./teacher-applicants-view";

vi.mock("next-auth/react", () => ({
  useSession: vi.fn(),
}));

vi.mocked(useSession).mockReturnValue({
  data: null,
  status: "unauthenticated",
  update: vi.fn(),
});

function makeData(
  overrides: Partial<SeminarApplicants> = {},
): SeminarApplicants[] {
  return [
    {
      seminar_id: "seminar-1",
      seminar_name: "AIゼミ",
      applicants: [
        {
          student_id: "s2322087",
          name: "橘 由翔",
          grade: "B4",
          priority: 1,
          reason: "機械学習を研究したいため。",
          past_seminars: [{ seminar_name: "旧ゼミ", academic_year: 2025 }],
        },
        {
          student_id: "s2422108",
          name: "阪田 琴美",
          grade: "B3",
          priority: 2,
          reason: "推薦システムに興味があるため。",
          past_seminars: [],
        },
      ],
      ...overrides,
    },
  ];
}

describe("TeacherApplicantsView", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders each seminar and applicant with priority label", () => {
    render(<TeacherApplicantsView initialData={makeData()} />);

    expect(screen.getByText("AIゼミ")).toBeInTheDocument();
    expect(screen.getByText("橘 由翔")).toBeInTheDocument();
    expect(screen.getByText("第1志望")).toBeInTheDocument();
    expect(screen.getByText("第2志望")).toBeInTheDocument();
  });

  it("shows a message when a seminar has no applicants", () => {
    render(
      <TeacherApplicantsView
        initialData={[
          { seminar_id: "seminar-2", seminar_name: "DBゼミ", applicants: [] },
        ]}
      />,
    );

    expect(screen.getByText("まだ応募者がいません。")).toBeInTheDocument();
  });

  it("shows a message when the teacher has no seminars", () => {
    render(<TeacherApplicantsView initialData={[]} />);

    expect(
      screen.getByText("担当しているゼミがありません。"),
    ).toBeInTheDocument();
  });

  it("expands to show the reason and past seminars on click", async () => {
    const user = userEvent.setup();
    render(<TeacherApplicantsView initialData={makeData()} />);

    expect(
      screen.queryByText("機械学習を研究したいため。"),
    ).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /橘 由翔/ }));

    expect(screen.getByText("機械学習を研究したいため。")).toBeInTheDocument();
    expect(screen.getByText("旧ゼミ(2025)")).toBeInTheDocument();
  });

  it("collapses again when clicked twice", async () => {
    const user = userEvent.setup();
    render(<TeacherApplicantsView initialData={makeData()} />);

    const toggle = screen.getByRole("button", { name: /橘 由翔/ });
    await user.click(toggle);
    await user.click(toggle);

    expect(
      screen.queryByText("機械学習を研究したいため。"),
    ).not.toBeInTheDocument();
  });

  it("shows 'なし' when an applicant has no past seminars", async () => {
    const user = userEvent.setup();
    render(<TeacherApplicantsView initialData={makeData()} />);

    await user.click(screen.getByRole("button", { name: /阪田 琴美/ }));

    expect(screen.getByText("なし")).toBeInTheDocument();
  });

  it("disables the CSV download button when there are no applicants", () => {
    render(<TeacherApplicantsView initialData={[]} />);

    expect(
      screen.getByRole("button", { name: "自分のゼミCSVダウンロード" }),
    ).toBeDisabled();
  });

  it("downloads the CSV via a blob link when clicked", async () => {
    const user = userEvent.setup();
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(new Response("csv content", { status: 200 }));
    const createObjectURL = vi
      .spyOn(URL, "createObjectURL")
      .mockReturnValue("blob:mock-url");
    const revokeObjectURL = vi
      .spyOn(URL, "revokeObjectURL")
      .mockImplementation(() => {});

    render(<TeacherApplicantsView initialData={makeData()} />);

    await user.click(
      screen.getByRole("button", { name: "自分のゼミCSVダウンロード" }),
    );

    expect(fetchSpy).toHaveBeenCalledWith(
      expect.stringContaining("/teacher/applicants.csv"),
      expect.anything(),
    );
    expect(createObjectURL).toHaveBeenCalled();
    expect(revokeObjectURL).toHaveBeenCalledWith("blob:mock-url");
  });

  it("shows an error message when the CSV download fails", async () => {
    const user = userEvent.setup();
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ detail: "権限がありません。" }), {
        status: 403,
      }),
    );

    render(<TeacherApplicantsView initialData={makeData()} />);

    await user.click(
      screen.getByRole("button", { name: "自分のゼミCSVダウンロード" }),
    );

    expect(await screen.findByText("権限がありません。")).toBeInTheDocument();
  });

  it("downloads the all-seminars CSV from the separate endpoint", async () => {
    const user = userEvent.setup();
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(new Response("csv content", { status: 200 }));
    vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:mock-url");
    vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => {});

    render(<TeacherApplicantsView initialData={makeData()} />);

    await user.click(
      screen.getByRole("button", { name: "全体CSVダウンロード" }),
    );

    expect(fetchSpy).toHaveBeenCalledWith(
      expect.stringContaining("/teacher/applicants/all.csv"),
      expect.anything(),
    );
  });

  it("does not disable the all-seminars CSV button when there are no applicants in the teacher's own seminars", () => {
    render(<TeacherApplicantsView initialData={[]} />);

    expect(
      screen.getByRole("button", { name: "全体CSVダウンロード" }),
    ).not.toBeDisabled();
  });
});
