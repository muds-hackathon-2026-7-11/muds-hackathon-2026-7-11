import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useSession } from "next-auth/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { FaqList, type Question } from "./faq-list";

vi.mock("next-auth/react", () => ({
  useSession: vi.fn(),
}));

vi.mocked(useSession).mockReturnValue({
  data: null,
  status: "unauthenticated",
  update: vi.fn(),
});

const questions: Question[] = [
  {
    id: "q1",
    content: "Pythonは必須ですか？",
    status: "answered",
    created_at: "2026-04-01T00:00:00Z",
    answers: [
      {
        id: "a1",
        content: "必須ではありませんが、経験があると望ましいです。",
        answerer_name: "山田教授",
        created_at: "2026-04-02T00:00:00Z",
      },
    ],
  },
  {
    id: "q2",
    content: "研究室に配属される時期はいつですか？",
    status: "waiting",
    created_at: "2026-04-03T00:00:00Z",
    answers: [],
  },
];

describe("FaqList", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders all questions and their answers", () => {
    render(<FaqList seminarId="seminar-1" questions={questions} />);

    expect(screen.getByText("Pythonは必須ですか？")).toBeInTheDocument();
    expect(
      screen.getByText("必須ではありませんが、経験があると望ましいです。"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("研究室に配属される時期はいつですか？"),
    ).toBeInTheDocument();
  });

  it("shows a placeholder for a question with no answers yet", () => {
    render(<FaqList seminarId="seminar-1" questions={questions} />);

    expect(screen.getByText("まだ回答がありません。")).toBeInTheDocument();
  });

  it("filters questions by keyword", async () => {
    const user = userEvent.setup();
    render(<FaqList seminarId="seminar-1" questions={questions} />);

    await user.type(screen.getByPlaceholderText("質問を検索"), "Python");

    expect(screen.getByText("Pythonは必須ですか？")).toBeInTheDocument();
    expect(
      screen.queryByText("研究室に配属される時期はいつですか？"),
    ).not.toBeInTheDocument();
  });

  it("filters case-insensitively", async () => {
    const user = userEvent.setup();
    render(<FaqList seminarId="seminar-1" questions={questions} />);

    await user.type(screen.getByPlaceholderText("質問を検索"), "python");

    expect(screen.getByText("Pythonは必須ですか？")).toBeInTheDocument();
  });

  it("matches keywords that only appear in an answer", async () => {
    const user = userEvent.setup();
    render(<FaqList seminarId="seminar-1" questions={questions} />);

    await user.type(screen.getByPlaceholderText("質問を検索"), "経験");

    expect(screen.getByText("Pythonは必須ですか？")).toBeInTheDocument();
    expect(
      screen.queryByText("研究室に配属される時期はいつですか？"),
    ).not.toBeInTheDocument();
  });

  it("shows a message when no question matches the keyword", async () => {
    const user = userEvent.setup();
    render(<FaqList seminarId="seminar-1" questions={questions} />);

    await user.type(
      screen.getByPlaceholderText("質問を検索"),
      "存在しない単語",
    );

    expect(
      screen.getByText("該当する質問が見つかりませんでした。"),
    ).toBeInTheDocument();
  });

  it("shows a message when there are no questions at all", () => {
    render(<FaqList seminarId="seminar-1" questions={[]} />);

    expect(
      screen.getByText("まだ質問が投稿されていません。"),
    ).toBeInTheDocument();
  });

  it("does not show the question form until the button is clicked", () => {
    render(<FaqList seminarId="seminar-1" questions={questions} />);

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("opens the question form when the button is clicked", async () => {
    const user = userEvent.setup();
    render(<FaqList seminarId="seminar-1" questions={questions} />);

    await user.click(screen.getByRole("button", { name: "質問する" }));

    expect(screen.getByRole("dialog")).toBeInTheDocument();
  });

  it("closes the question form when cancelled", async () => {
    const user = userEvent.setup();
    render(<FaqList seminarId="seminar-1" questions={questions} />);

    await user.click(screen.getByRole("button", { name: "質問する" }));
    await user.click(screen.getByRole("button", { name: "キャンセル" }));

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("submits a new question and prepends it to the list", async () => {
    const user = userEvent.setup();
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          id: "q3",
          seminar_id: "seminar-1",
          content: "新しい質問です",
          status: "waiting",
          created_at: "2026-04-04T00:00:00Z",
        }),
        { status: 201 },
      ),
    );

    render(<FaqList seminarId="seminar-1" questions={questions} />);

    await user.click(screen.getByRole("button", { name: "質問する" }));
    await user.type(
      screen.getByPlaceholderText("ゼミへの質問を入力してください"),
      "新しい質問です",
    );
    await user.click(screen.getByRole("button", { name: "質問を送信" }));

    expect(await screen.findByText("新しい質問です")).toBeInTheDocument();
    expect(fetchSpy).toHaveBeenCalledWith(
      expect.stringContaining("/questions/me"),
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          seminar_id: "seminar-1",
          content: "新しい質問です",
        }),
      }),
    );
  });

  it("shows an error when submitting without content", async () => {
    const user = userEvent.setup();
    const fetchSpy = vi.spyOn(globalThis, "fetch");

    render(<FaqList seminarId="seminar-1" questions={questions} />);

    await user.click(screen.getByRole("button", { name: "質問する" }));
    await user.click(screen.getByRole("button", { name: "質問を送信" }));

    expect(
      await screen.findByText("質問内容を入力してください。"),
    ).toBeInTheDocument();
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("shows the error message when submission fails", async () => {
    const user = userEvent.setup();
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({ detail: "指定されたゼミが見つかりません。" }),
        {
          status: 404,
        },
      ),
    );

    render(<FaqList seminarId="seminar-1" questions={questions} />);

    await user.click(screen.getByRole("button", { name: "質問する" }));
    await user.type(
      screen.getByPlaceholderText("ゼミへの質問を入力してください"),
      "質問",
    );
    await user.click(screen.getByRole("button", { name: "質問を送信" }));

    expect(
      await screen.findByText("指定されたゼミが見つかりません。"),
    ).toBeInTheDocument();
  });
});
