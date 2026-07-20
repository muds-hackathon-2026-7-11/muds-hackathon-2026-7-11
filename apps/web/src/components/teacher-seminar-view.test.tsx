import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useSession } from "next-auth/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import {
  TeacherSeminarView,
  type TeacherSeminar,
} from "./teacher-seminar-view";

vi.mock("next-auth/react", () => ({
  useSession: vi.fn(),
}));

vi.mocked(useSession).mockReturnValue({
  data: null,
  status: "unauthenticated",
  update: vi.fn(),
});

function makeSeminar(overrides: Partial<TeacherSeminar> = {}): TeacherSeminar {
  return {
    id: "seminar-1",
    name: "AIゼミ",
    description: "機械学習を中心に研究しています。",
    photo_url: null,
    materials: [
      { id: "material-1", url: "https://example.com/slide.pdf", type: "pdf" },
    ],
    capacity: 10,
    ...overrides,
  };
}

describe("TeacherSeminarView", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders the seminar name, description, and materials", () => {
    render(<TeacherSeminarView initialSeminars={[makeSeminar()]} />);

    expect(screen.getByText("AIゼミ")).toBeInTheDocument();
    expect(
      screen.getByText("機械学習を中心に研究しています。"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("https://example.com/slide.pdf"),
    ).toBeInTheDocument();
  });

  it("shows a message when the teacher has no seminars", () => {
    render(<TeacherSeminarView initialSeminars={[]} />);

    expect(
      screen.getByText("担当しているゼミがありません。"),
    ).toBeInTheDocument();
  });

  it("shows a message when there are no materials", () => {
    render(
      <TeacherSeminarView initialSeminars={[makeSeminar({ materials: [] })]} />,
    );

    expect(screen.getByText("資料はまだありません。")).toBeInTheDocument();
  });

  it("edits the description and photo_url", async () => {
    const user = userEvent.setup();
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(
        new Response(
          JSON.stringify(
            makeSeminar({ description: "更新後の説明", photo_url: null }),
          ),
          { status: 200 },
        ),
      );

    render(<TeacherSeminarView initialSeminars={[makeSeminar()]} />);

    await user.click(screen.getByRole("button", { name: "編集" }));
    const textarea = screen.getByPlaceholderText("研究内容・ゼミ紹介文");
    await user.clear(textarea);
    await user.type(textarea, "更新後の説明");
    await user.click(screen.getByRole("button", { name: "保存する" }));

    expect(fetchSpy).toHaveBeenCalledWith(
      expect.stringContaining("/teacher/seminars/seminar-1"),
      expect.objectContaining({ method: "PATCH" }),
    );
    expect(await screen.findByText("更新後の説明")).toBeInTheDocument();
  });

  it("cancels editing without saving", async () => {
    const user = userEvent.setup();
    const fetchSpy = vi.spyOn(globalThis, "fetch");

    render(<TeacherSeminarView initialSeminars={[makeSeminar()]} />);

    await user.click(screen.getByRole("button", { name: "編集" }));
    await user.click(screen.getByRole("button", { name: "キャンセル" }));

    expect(fetchSpy).not.toHaveBeenCalled();
    expect(
      screen.getByText("機械学習を中心に研究しています。"),
    ).toBeInTheDocument();
  });

  it("adds a material", async () => {
    const user = userEvent.setup();
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          id: "material-2",
          url: "https://example.com/new.pdf",
          type: "slide",
        }),
        { status: 201 },
      ),
    );

    render(
      <TeacherSeminarView initialSeminars={[makeSeminar({ materials: [] })]} />,
    );

    await user.type(
      screen.getByPlaceholderText("資料のURL"),
      "https://example.com/new.pdf",
    );
    await user.click(screen.getByRole("button", { name: "追加" }));

    expect(
      await screen.findByText("https://example.com/new.pdf"),
    ).toBeInTheDocument();
  });

  it("shows an error when adding a material without a URL", async () => {
    const user = userEvent.setup();
    const fetchSpy = vi.spyOn(globalThis, "fetch");

    render(<TeacherSeminarView initialSeminars={[makeSeminar()]} />);

    await user.click(screen.getByRole("button", { name: "追加" }));

    expect(
      await screen.findByText("資料のURLを入力してください。"),
    ).toBeInTheDocument();
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("deletes a material", async () => {
    const user = userEvent.setup();
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(null, { status: 204 }),
    );

    render(<TeacherSeminarView initialSeminars={[makeSeminar()]} />);

    await user.click(screen.getByRole("button", { name: "削除" }));

    expect(
      await screen.findByText("資料はまだありません。"),
    ).toBeInTheDocument();
  });

  it("shows an error message when saving fails", async () => {
    const user = userEvent.setup();
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({ detail: "担当していないゼミは操作できません。" }),
        {
          status: 403,
        },
      ),
    );

    render(<TeacherSeminarView initialSeminars={[makeSeminar()]} />);

    await user.click(screen.getByRole("button", { name: "編集" }));
    await user.click(screen.getByRole("button", { name: "保存する" }));

    expect(
      await screen.findByText("担当していないゼミは操作できません。"),
    ).toBeInTheDocument();
  });

  it("saves the capacity", async () => {
    const user = userEvent.setup();
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(
        new Response(JSON.stringify({ capacity: 20 }), { status: 200 }),
      );

    render(<TeacherSeminarView initialSeminars={[makeSeminar()]} />);

    const capacityInput = screen.getByPlaceholderText("人数");
    await user.clear(capacityInput);
    await user.type(capacityInput, "20");
    await user.click(screen.getByRole("button", { name: "定員を保存する" }));

    expect(fetchSpy).toHaveBeenCalledWith(
      expect.stringContaining("/teacher/seminars/seminar-1/recruitment"),
      expect.objectContaining({
        method: "PATCH",
        body: JSON.stringify({ capacity: 20 }),
      }),
    );
    await screen.findByRole("button", { name: "定員を保存する" });
    expect(capacityInput).toHaveValue(20);
  });

  it("rejects a non-numeric capacity without calling the API", async () => {
    const user = userEvent.setup();
    const fetchSpy = vi.spyOn(globalThis, "fetch");

    render(<TeacherSeminarView initialSeminars={[makeSeminar()]} />);

    const capacityInput = screen.getByPlaceholderText("人数");
    await user.clear(capacityInput);
    await user.click(screen.getByRole("button", { name: "定員を保存する" }));

    expect(
      await screen.findByText("定員は0以上の整数で入力してください。"),
    ).toBeInTheDocument();
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it.each([
    ["1.5", "小数"],
    ["-1", "負の数"],
  ])("rejects a %s capacity (%s) without calling the API", async (value) => {
    const user = userEvent.setup();
    const fetchSpy = vi.spyOn(globalThis, "fetch");

    render(<TeacherSeminarView initialSeminars={[makeSeminar()]} />);

    const capacityInput = screen.getByPlaceholderText("人数");
    await user.clear(capacityInput);
    await user.type(capacityInput, value);
    await user.click(screen.getByRole("button", { name: "定員を保存する" }));

    expect(
      await screen.findByText("定員は0以上の整数で入力してください。"),
    ).toBeInTheDocument();
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("keeps a capacity error visible after an unrelated description save succeeds", async () => {
    const user = userEvent.setup();
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify(makeSeminar()), { status: 200 }),
    );

    render(<TeacherSeminarView initialSeminars={[makeSeminar()]} />);

    const capacityInput = screen.getByPlaceholderText("人数");
    await user.clear(capacityInput);
    await user.click(screen.getByRole("button", { name: "定員を保存する" }));
    expect(
      await screen.findByText("定員は0以上の整数で入力してください。"),
    ).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "編集" }));
    await user.click(screen.getByRole("button", { name: "保存する" }));

    // 紹介文の保存(別フローの成功)が定員側のエラー表示を消してしまわない。
    expect(
      screen.getByText("定員は0以上の整数で入力してください。"),
    ).toBeInTheDocument();
  });

  it("shows an error when there is no active recruitment round", async () => {
    const user = userEvent.setup();
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({ detail: "現在募集中の期間がありません。" }),
        { status: 400 },
      ),
    );

    render(<TeacherSeminarView initialSeminars={[makeSeminar()]} />);

    const capacityInput = screen.getByPlaceholderText("人数");
    await user.clear(capacityInput);
    await user.type(capacityInput, "5");
    await user.click(screen.getByRole("button", { name: "定員を保存する" }));

    expect(
      await screen.findByText("現在募集中の期間がありません。"),
    ).toBeInTheDocument();
  });
});
