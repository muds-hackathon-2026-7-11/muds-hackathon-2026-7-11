import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { Session } from "next-auth";
import { useSession } from "next-auth/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AiSeminarChatView } from "./ai-seminar-chat-view";

vi.mock("next-auth/react", () => ({
  useSession: vi.fn(),
}));

type Recommendation = { seminar_name: string; reason: string };

function mockConsult(reply: string, recommendations: Recommendation[] = []) {
  return vi
    .spyOn(globalThis, "fetch")
    .mockResolvedValue(
      new Response(JSON.stringify({ reply, recommendations }), { status: 200 }),
    );
}

const PLACEHOLDER = "やりたいことを入力";

beforeEach(() => {
  vi.mocked(useSession).mockReturnValue({
    data: { accessToken: "test-token" } as Session,
    status: "authenticated",
    update: vi.fn(),
  } as ReturnType<typeof useSession>);
  // jsdom は scrollIntoView を実装していないため、自動スクロールをスタブする。
  Element.prototype.scrollIntoView = vi.fn();
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("AiSeminarChatView", () => {
  it("shows the greeting on first render", () => {
    render(<AiSeminarChatView />);
    expect(screen.getByText(/あなたに合いそうなゼミ/)).toBeInTheDocument();
  });

  it("disables the send button while the input is empty", () => {
    render(<AiSeminarChatView />);
    expect(screen.getByRole("button", { name: "送信" })).toBeDisabled();
  });

  it("posts to /consult and shows the reply and recommendations", async () => {
    const user = userEvent.setup();
    const fetchSpy = mockConsult("中村ゼミがおすすめです。", [
      { seminar_name: "中村ゼミ", reason: "機械学習に強い" },
    ]);
    render(<AiSeminarChatView />);

    await user.type(
      screen.getByPlaceholderText(PLACEHOLDER),
      "機械学習をやりたい",
    );
    await user.click(screen.getByRole("button", { name: "送信" }));

    // 自分の発話とbotの返答、推薦ゼミが表示される
    expect(screen.getByText("機械学習をやりたい")).toBeInTheDocument();
    expect(
      await screen.findByText("中村ゼミがおすすめです。"),
    ).toBeInTheDocument();
    expect(screen.getByText("中村ゼミ")).toBeInTheDocument();
    expect(screen.getByText("機械学習に強い")).toBeInTheDocument();

    const [url, init] = fetchSpy.mock.calls[0] as [string, RequestInit];
    expect(url).toContain("/consult");
    expect(init.method).toBe("POST");
    const body = JSON.parse(init.body as string);
    expect(body.message).toBe("機械学習をやりたい");
    expect(body.history).toEqual([]); // 最初の送信は履歴が空
  });

  it("includes prior turns as history on the next message", async () => {
    const user = userEvent.setup();
    const fetchSpy = mockConsult("返答1");
    render(<AiSeminarChatView />);
    const input = screen.getByPlaceholderText(PLACEHOLDER);

    await user.type(input, "一通目");
    await user.click(screen.getByRole("button", { name: "送信" }));
    await screen.findByText("返答1");

    await user.type(input, "二通目");
    await user.click(screen.getByRole("button", { name: "送信" }));

    await waitFor(() => expect(fetchSpy).toHaveBeenCalledTimes(2));
    const body = JSON.parse(
      (fetchSpy.mock.calls[1][1] as RequestInit).body as string,
    );
    expect(body.message).toBe("二通目");
    expect(body.history).toEqual([
      { role: "user", content: "一通目" },
      { role: "assistant", content: "返答1" },
    ]);
  });

  it("shows a fallback message when the request fails", async () => {
    const user = userEvent.setup();
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response("", { status: 500 }),
    );
    render(<AiSeminarChatView />);

    await user.type(screen.getByPlaceholderText(PLACEHOLDER), "test");
    await user.click(screen.getByRole("button", { name: "送信" }));

    expect(
      await screen.findByText(/うまく応答できませんでした/),
    ).toBeInTheDocument();
  });
});
