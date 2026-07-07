import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { Session } from "next-auth";
import { useSession } from "next-auth/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { SeminarDetailView, type SeminarDetail } from "./seminar-detail";

vi.mock("next-auth/react", () => ({
  useSession: vi.fn(),
}));

const seminar: SeminarDetail = {
  id: "seminar-1",
  name: "AIゼミ",
  description: "機械学習の研究をします。",
  photo_url: null,
  capacity: 10,
  teachers: [
    {
      id: "teacher-1",
      name: "山田教授",
      photo_url: null,
      research_theme: "深層学習",
      interest_tags: [
        { id: "tag-1", name: "深層学習", category: "AI・機械学習" },
      ],
    },
  ],
  materials: [
    { id: "material-1", url: "https://example.com/a.pdf", type: "pdf" },
  ],
  current_members: [
    {
      id: "member-1",
      name: "学生A",
      research_theme: "画像認識",
      interest_tags: [
        { id: "tag-2", name: "画像認識", category: "画像・映像" },
      ],
    },
    {
      id: "member-2",
      name: "学生B",
      research_theme: "自然言語処理",
      interest_tags: [
        { id: "tag-2", name: "画像認識", category: "画像・映像" },
      ],
    },
  ],
};

beforeEach(() => {
  vi.mocked(useSession).mockReturnValue({
    data: { accessToken: "test-token" } as Session,
    status: "authenticated",
    update: vi.fn(),
  } as ReturnType<typeof useSession>);
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("SeminarDetailView", () => {
  it("renders seminar info, teachers, materials, and current members", () => {
    render(<SeminarDetailView seminar={seminar} slackUserId="U123" />);

    expect(screen.getByText("AIゼミ")).toBeInTheDocument();
    expect(screen.getByText("機械学習の研究をします。")).toBeInTheDocument();
    expect(screen.getByText("山田教授")).toBeInTheDocument();
    expect(screen.getByText("PDF")).toBeInTheDocument();
    expect(screen.getByText("学生A")).toBeInTheDocument();
    expect(screen.getByText("学生B")).toBeInTheDocument();
    expect(screen.getByText("2人")).toBeInTheDocument();
  });

  it("shows the teacher's initial when no photo_url is set", () => {
    render(<SeminarDetailView seminar={seminar} slackUserId="U123" />);

    expect(screen.getByText("山")).toBeInTheDocument();
    expect(screen.queryByAltText("山田教授")).not.toBeInTheDocument();
  });

  it("shows the teacher's photo when photo_url is set", () => {
    const withPhoto: SeminarDetail = {
      ...seminar,
      teachers: [
        { ...seminar.teachers[0], photo_url: "https://example.com/p.jpg" },
      ],
    };
    render(<SeminarDetailView seminar={withPhoto} slackUserId="U123" />);

    expect(screen.getByAltText("山田教授")).toHaveAttribute(
      "src",
      "https://example.com/p.jpg",
    );
  });

  it("aggregates member interest tags into a chart with counts", () => {
    render(<SeminarDetailView seminar={seminar} slackUserId="U123" />);

    // 画像認識タグは学生A・学生Bの両方が持つため、研究概要・タグ表示・
    // グラフの軸ラベルなど複数箇所に現れる。
    expect(screen.getAllByText("画像認識").length).toBeGreaterThan(0);
  });

  it("shows a Slack-link message instead of the ask button when slackUserId is null", () => {
    render(<SeminarDetailView seminar={seminar} slackUserId={null} />);

    expect(
      screen.getByText("質問するにはSlack連携が必要です。"),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "質問する" }),
    ).not.toBeInTheDocument();
  });

  it("submits a question and shows a confirmation message", async () => {
    const user = userEvent.setup();
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(new Response(JSON.stringify({}), { status: 201 }));

    render(<SeminarDetailView seminar={seminar} slackUserId="U123" />);

    await user.click(screen.getByRole("button", { name: "質問する" }));
    await user.type(
      screen.getByPlaceholderText("質問内容を入力してください"),
      "質問です",
    );
    await user.click(screen.getByRole("button", { name: "送信" }));

    await waitFor(() => {
      expect(
        screen.getByText("質問を投稿しました。回答があるとSlackに届きます。"),
      ).toBeInTheDocument();
    });

    const [url, init] = fetchSpy.mock.calls[0] as [string, RequestInit];
    expect(url).toContain("/questions");
    const body = JSON.parse(init.body as string);
    expect(body).toEqual({
      seminar_id: "seminar-1",
      slack_user_id: "U123",
      content: "質問です",
    });
  });
});
