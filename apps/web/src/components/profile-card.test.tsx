import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { Session } from "next-auth";
import { useSession } from "next-auth/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ProfileCard, type ResearchTag } from "./profile-card";

vi.mock("next-auth/react", () => ({
  useSession: vi.fn(),
}));

const allTags: ResearchTag[] = [
  { id: "tag-1", name: "機械学習", category: "AI・機械学習" },
  { id: "tag-2", name: "画像処理", category: "画像・映像" },
];

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

describe("ProfileCard", () => {
  it("renders the name, email, grade, research title, and research theme", () => {
    render(
      <ProfileCard
        name="山田 太郎"
        email="s2300000@stu.musashino-u.ac.jp"
        grade="B3"
        researchTitle="音声認識モデルの研究"
        researchTheme="音声処理の研究"
      />,
    );

    expect(screen.getByText("山田 太郎")).toBeInTheDocument();
    expect(
      screen.getByText("s2300000@stu.musashino-u.ac.jp"),
    ).toBeInTheDocument();
    expect(screen.getByText("B3")).toBeInTheDocument();
    expect(screen.getByText("音声認識モデルの研究")).toBeInTheDocument();
    expect(screen.getByText("音声処理の研究")).toBeInTheDocument();
  });

  it("keeps a different faculty's grade string as-is (e.g. MIDS)", () => {
    render(
      <ProfileCard
        name="佐藤 花子"
        email="s2300001@stu.musashino-u.ac.jp"
        grade="MIDS/B1"
        researchTitle={null}
        researchTheme={null}
      />,
    );

    expect(screen.getByText("MIDS/B1")).toBeInTheDocument();
  });

  it("falls back to a placeholder when grade, researchTitle, or researchTheme is missing", () => {
    render(
      <ProfileCard
        name="山田 太郎"
        email="s2300000@stu.musashino-u.ac.jp"
        grade={null}
        researchTitle={null}
        researchTheme={null}
      />,
    );

    expect(screen.getAllByText("未設定")).toHaveLength(2);
    expect(screen.getByText("研究タイトル未設定")).toBeInTheDocument();
  });

  it("renders the currently set interest tags", () => {
    render(
      <ProfileCard
        name="山田 太郎"
        email="s2300000@stu.musashino-u.ac.jp"
        grade="B3"
        researchTitle="音声認識モデルの研究"
        researchTheme="音声処理の研究"
        interestTags={[allTags[0]]}
        allTags={allTags}
      />,
    );

    expect(screen.getByText("機械学習")).toBeInTheDocument();
    expect(screen.queryByText("画像処理")).not.toBeInTheDocument();
  });

  it("enters edit mode and saves the updated research title, theme, and tags", async () => {
    const user = userEvent.setup();
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          research_title: "新しいタイトル",
          research_theme: "新しい研究テーマ",
          interest_tags: [allTags[1]],
        }),
        { status: 200 },
      ),
    );

    render(
      <ProfileCard
        name="山田 太郎"
        email="s2300000@stu.musashino-u.ac.jp"
        grade="B3"
        researchTitle="音声認識モデルの研究"
        researchTheme="音声処理の研究"
        interestTags={[allTags[0]]}
        allTags={allTags}
      />,
    );

    await user.click(screen.getByRole("button", { name: "編集" }));

    const dialog = within(screen.getByRole("dialog"));
    const titleInput = dialog.getByPlaceholderText(
      "研究タイトルを入力してください",
    );
    await user.clear(titleInput);
    await user.type(titleInput, "新しいタイトル");
    const textarea = dialog.getByPlaceholderText("研究概要を入力してください");
    await user.clear(textarea);
    await user.type(textarea, "新しい研究テーマ");
    await user.click(dialog.getByText("画像処理"));
    await user.click(dialog.getByText("機械学習"));
    await user.click(dialog.getByRole("button", { name: "保存" }));

    await waitFor(() => {
      expect(screen.getByText("新しいタイトル")).toBeInTheDocument();
    });
    expect(screen.getByText("新しい研究テーマ")).toBeInTheDocument();
    expect(screen.getByText("画像処理")).toBeInTheDocument();
    expect(screen.queryByText("機械学習")).not.toBeInTheDocument();

    const [url, init] = fetchSpy.mock.calls[0] as [string, RequestInit];
    expect(url).toContain("/me");
    expect(init.method).toBe("PATCH");
    const body = JSON.parse(init.body as string);
    expect(body.research_title).toBe("新しいタイトル");
    expect(body.research_theme).toBe("新しい研究テーマ");
    expect(body.interest_tag_ids).toEqual(["tag-2"]);
  });

  it("discards changes when cancel is clicked", async () => {
    const user = userEvent.setup();
    const fetchSpy = vi.spyOn(globalThis, "fetch");

    render(
      <ProfileCard
        name="山田 太郎"
        email="s2300000@stu.musashino-u.ac.jp"
        grade="B3"
        researchTitle="音声認識モデルの研究"
        researchTheme="音声処理の研究"
        allTags={allTags}
      />,
    );

    await user.click(screen.getByRole("button", { name: "編集" }));
    const titleInput = screen.getByPlaceholderText(
      "研究タイトルを入力してください",
    );
    await user.clear(titleInput);
    await user.type(titleInput, "書きかけのタイトル");
    const textarea = screen.getByPlaceholderText("研究概要を入力してください");
    await user.clear(textarea);
    await user.type(textarea, "書きかけの内容");
    await user.click(screen.getByRole("button", { name: "キャンセル" }));

    expect(screen.getByText("音声認識モデルの研究")).toBeInTheDocument();
    expect(screen.getByText("音声処理の研究")).toBeInTheDocument();
    expect(
      screen.queryByPlaceholderText("研究概要を入力してください"),
    ).not.toBeInTheDocument();
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("closes when the backdrop is clicked, but not when the dialog itself is clicked", async () => {
    const user = userEvent.setup();

    render(
      <ProfileCard
        name="山田 太郎"
        email="s2300000@stu.musashino-u.ac.jp"
        grade="B3"
        researchTitle="音声認識モデルの研究"
        researchTheme="音声処理の研究"
        allTags={allTags}
      />,
    );

    await user.click(screen.getByRole("button", { name: "編集" }));
    const dialog = screen.getByRole("dialog");

    await user.click(dialog);
    expect(screen.getByRole("dialog")).toBeInTheDocument();

    const backdrop = dialog.parentElement as HTMLElement;
    await user.click(backdrop);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("caps tag selection at 20 and disables further unselected tags", async () => {
    const user = userEvent.setup();
    const manyTags: ResearchTag[] = Array.from({ length: 21 }, (_, i) => ({
      id: `tag-${i}`,
      name: `タグ${i}`,
      category: "カテゴリ",
    }));

    render(
      <ProfileCard
        name="山田 太郎"
        email="s2300000@stu.musashino-u.ac.jp"
        grade="B3"
        researchTitle="音声認識モデルの研究"
        researchTheme="音声処理の研究"
        interestTags={manyTags.slice(0, 20)}
        allTags={manyTags}
      />,
    );

    await user.click(screen.getByRole("button", { name: "編集" }));
    const dialog = within(screen.getByRole("dialog"));

    expect(dialog.getByText("タグ(20/20)")).toBeInTheDocument();

    const unselectedCheckbox = dialog.getByRole("checkbox", {
      name: "タグ20",
    });
    expect(unselectedCheckbox).toBeDisabled();

    await user.click(dialog.getByText("タグ20"));
    expect(dialog.getByText("タグ(20/20)")).toBeInTheDocument();
  });

  it("closes when Escape is pressed", async () => {
    const user = userEvent.setup();

    render(
      <ProfileCard
        name="山田 太郎"
        email="s2300000@stu.musashino-u.ac.jp"
        grade="B3"
        researchTitle="音声認識モデルの研究"
        researchTheme="音声処理の研究"
        allTags={allTags}
      />,
    );

    await user.click(screen.getByRole("button", { name: "編集" }));
    expect(screen.getByRole("dialog")).toBeInTheDocument();

    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
});
