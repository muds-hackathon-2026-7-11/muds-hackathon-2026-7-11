import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { AiSeminarChatView } from "./ai-seminar-chat-view";

describe("AiSeminarChatView", () => {
  it("renders the sample conversation and a disabled composer", () => {
    render(<AiSeminarChatView />);

    expect(screen.getByText("AIゼミ相談")).toBeInTheDocument();
    expect(
      screen.getByText(/やってみたいことや興味のある分野/),
    ).toBeInTheDocument();
    expect(
      screen.getByPlaceholderText("やりたいことを入力"),
    ).toBeDisabled();
    expect(screen.getByRole("button", { name: "送信" })).toBeDisabled();
  });
});
