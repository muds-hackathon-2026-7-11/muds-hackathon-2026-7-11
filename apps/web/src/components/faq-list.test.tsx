import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { FaqList, type Question } from "./faq-list";

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
  it("renders all questions and their answers", () => {
    render(<FaqList questions={questions} />);

    expect(screen.getByText("Pythonは必須ですか？")).toBeInTheDocument();
    expect(
      screen.getByText("必須ではありませんが、経験があると望ましいです。"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("研究室に配属される時期はいつですか？"),
    ).toBeInTheDocument();
  });

  it("shows a placeholder for a question with no answers yet", () => {
    render(<FaqList questions={questions} />);

    expect(screen.getByText("まだ回答がありません。")).toBeInTheDocument();
  });

  it("filters questions by keyword", async () => {
    const user = userEvent.setup();
    render(<FaqList questions={questions} />);

    await user.type(screen.getByPlaceholderText("質問を検索"), "Python");

    expect(screen.getByText("Pythonは必須ですか？")).toBeInTheDocument();
    expect(
      screen.queryByText("研究室に配属される時期はいつですか？"),
    ).not.toBeInTheDocument();
  });

  it("shows a message when no question matches the keyword", async () => {
    const user = userEvent.setup();
    render(<FaqList questions={questions} />);

    await user.type(
      screen.getByPlaceholderText("質問を検索"),
      "存在しない単語",
    );

    expect(
      screen.getByText("該当する質問が見つかりませんでした。"),
    ).toBeInTheDocument();
  });

  it("shows a message when there are no questions at all", () => {
    render(<FaqList questions={[]} />);

    expect(
      screen.getByText("まだ質問が投稿されていません。"),
    ).toBeInTheDocument();
  });
});
