import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useSession } from "next-auth/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import {
  AdminSeminarsView,
  type AdminSeminar,
  type AdminTeacherOption,
} from "./admin-seminars-view";

vi.mock("next-auth/react", () => ({
  useSession: vi.fn(),
}));

vi.mocked(useSession).mockReturnValue({
  data: null,
  status: "unauthenticated",
  update: vi.fn(),
});

function makeSeminar(overrides: Partial<AdminSeminar> = {}): AdminSeminar {
  return {
    id: "seminar-1",
    name: "AIゼミ",
    description: "説明文",
    photo_url: null,
    teachers: [],
    materials: [],
    ...overrides,
  };
}

function makeTeacher(
  overrides: Partial<AdminTeacherOption> = {},
): AdminTeacherOption {
  return {
    id: "teacher-1",
    name: "山田先生",
    email: "yamada@example.com",
    research_theme: null,
    photo_url: null,
    is_active: true,
    ...overrides,
  };
}

type RenderOverrides = {
  seminars?: AdminSeminar[];
  teachers?: AdminTeacherOption[];
};

function renderView(overrides: RenderOverrides = {}) {
  return render(
    <AdminSeminarsView
      initialSeminars={overrides.seminars ?? []}
      teacherOptions={overrides.teachers ?? []}
    />,
  );
}

describe("AdminSeminarsView", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders existing seminars and their assigned teachers", () => {
    const teacher = makeTeacher();
    const seminar = makeSeminar({
      teachers: [{ id: teacher.id, name: teacher.name }],
    });
    renderView({ seminars: [seminar], teachers: [teacher] });

    expect(screen.getByText("AIゼミ")).toBeInTheDocument();
    const checkbox = screen.getByRole("checkbox", { name: /山田先生/ });
    expect(checkbox).toBeChecked();
  });

  it("links to the recruitment term management screen", () => {
    renderView();

    expect(
      screen.getByRole("link", { name: "募集ラウンド管理" }),
    ).toHaveAttribute("href", "/admin/recruitment-terms");
  });

  it("shows the seminar's id for use in the assignment import CSV's seminar_id column", () => {
    const seminar = makeSeminar({ id: "seminar-abc-123" });
    renderView({ seminars: [seminar] });

    expect(screen.getByText("seminar-abc-123")).toBeInTheDocument();
  });

  it("does not show the create form until the toggle button is clicked", async () => {
    const user = userEvent.setup();
    renderView();

    expect(screen.queryByPlaceholderText("ゼミ名")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "+ 新規ゼミを作成" }));
    expect(screen.getByPlaceholderText("ゼミ名")).toBeInTheDocument();
  });

  it("hides the create form again when cancelled", async () => {
    const user = userEvent.setup();
    renderView();

    await user.click(screen.getByRole("button", { name: "+ 新規ゼミを作成" }));
    await user.type(screen.getByPlaceholderText("ゼミ名"), "途中まで入力");
    await user.click(screen.getByRole("button", { name: "キャンセル" }));

    expect(screen.queryByPlaceholderText("ゼミ名")).not.toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "+ 新規ゼミを作成" }),
    ).toBeInTheDocument();
  });

  it("creates a new seminar (including its icon) and shows it in the list", async () => {
    const user = userEvent.setup();
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          id: "seminar-2",
          name: "新ゼミ",
          description: null,
          photo_url: "https://example.com/icon.png",
          teachers: [],
          materials: [],
        }),
        { status: 201 },
      ),
    );

    renderView();

    await user.click(screen.getByRole("button", { name: "+ 新規ゼミを作成" }));
    await user.type(screen.getByPlaceholderText("ゼミ名"), "新ゼミ");
    await user.type(
      screen.getByPlaceholderText("アイコン画像のURL(任意)"),
      "https://example.com/icon.png",
    );
    await user.click(screen.getByRole("button", { name: "作成する" }));

    expect(await screen.findByText("新ゼミ")).toBeInTheDocument();
    expect(fetchSpy).toHaveBeenCalledWith(
      expect.stringContaining("/admin/seminars"),
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          name: "新ゼミ",
          description: null,
          photo_url: "https://example.com/icon.png",
        }),
      }),
    );
    // 作成成功後はフォームが閉じ、トグルボタンに戻る
    expect(
      screen.getByRole("button", { name: "+ 新規ゼミを作成" }),
    ).toBeInTheDocument();
  });

  it("shows an error and does not add a seminar when the name is empty", async () => {
    const user = userEvent.setup();
    const fetchSpy = vi.spyOn(globalThis, "fetch");

    renderView();
    await user.click(screen.getByRole("button", { name: "+ 新規ゼミを作成" }));
    await user.click(screen.getByRole("button", { name: "作成する" }));

    expect(
      await screen.findByText("ゼミ名を入力してください。"),
    ).toBeInTheDocument();
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("edits a seminar's name and description", async () => {
    const user = userEvent.setup();
    const seminar = makeSeminar();
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ ...seminar, name: "改名後" }), {
        status: 200,
      }),
    );

    renderView({ seminars: [seminar] });

    await user.click(screen.getByRole("button", { name: "編集" }));
    const nameInput = screen.getByDisplayValue("AIゼミ");
    await user.clear(nameInput);
    await user.type(nameInput, "改名後");
    await user.click(screen.getByRole("button", { name: "保存する" }));

    expect(await screen.findByText("改名後")).toBeInTheDocument();
  });

  it("shows an icon preview when photo_url is set", () => {
    const seminar = makeSeminar({ photo_url: "https://example.com/icon.png" });
    renderView({ seminars: [seminar] });

    const icon = screen.getByRole("img");
    expect(icon).toHaveAttribute("src", "https://example.com/icon.png");
  });

  it("does not show an icon when photo_url is not set", () => {
    const seminar = makeSeminar({ photo_url: null });
    renderView({ seminars: [seminar] });

    expect(screen.queryByRole("img")).not.toBeInTheDocument();
  });

  it("edits a seminar's icon URL", async () => {
    const user = userEvent.setup();
    const seminar = makeSeminar({ photo_url: null });
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          ...seminar,
          photo_url: "https://example.com/new-icon.png",
        }),
        { status: 200 },
      ),
    );

    renderView({ seminars: [seminar] });

    await user.click(screen.getByRole("button", { name: "編集" }));
    await user.type(
      screen.getByPlaceholderText("アイコン画像のURL(任意)"),
      "https://example.com/new-icon.png",
    );
    await user.click(screen.getByRole("button", { name: "保存する" }));

    await waitFor(() => {
      expect(fetchSpy).toHaveBeenCalledWith(
        expect.stringContaining(`/admin/seminars/${seminar.id}`),
        expect.objectContaining({
          method: "PATCH",
          body: JSON.stringify({
            name: seminar.name,
            description: seminar.description,
            photo_url: "https://example.com/new-icon.png",
          }),
        }),
      );
    });
    expect(await screen.findByRole("img")).toHaveAttribute(
      "src",
      "https://example.com/new-icon.png",
    );
  });

  it("removes a seminar after confirming deletion", async () => {
    const user = userEvent.setup();
    const seminar = makeSeminar();
    vi.spyOn(window, "confirm").mockReturnValue(true);
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(null, { status: 204 }),
    );

    renderView({ seminars: [seminar] });
    await user.click(screen.getByRole("button", { name: "削除" }));

    await waitFor(() => {
      expect(screen.queryByText("AIゼミ")).not.toBeInTheDocument();
    });
  });

  it("does not delete a seminar when the confirmation is cancelled", async () => {
    const user = userEvent.setup();
    const seminar = makeSeminar();
    vi.spyOn(window, "confirm").mockReturnValue(false);
    const fetchSpy = vi.spyOn(globalThis, "fetch");

    renderView({ seminars: [seminar] });
    await user.click(screen.getByRole("button", { name: "削除" }));

    expect(fetchSpy).not.toHaveBeenCalled();
    expect(screen.getByText("AIゼミ")).toBeInTheDocument();
  });

  it("assigns a teacher when the checkbox is checked", async () => {
    const user = userEvent.setup();
    const seminar = makeSeminar();
    const teacher = makeTeacher();
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(null, { status: 204 }),
    );

    renderView({ seminars: [seminar], teachers: [teacher] });

    const checkbox = screen.getByRole("checkbox", { name: /山田先生/ });
    expect(checkbox).not.toBeChecked();
    await user.click(checkbox);

    await waitFor(() => expect(checkbox).toBeChecked());
    expect(globalThis.fetch).toHaveBeenCalledWith(
      expect.stringContaining(
        `/admin/seminars/${seminar.id}/teachers/${teacher.id}`,
      ),
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("adds a material and shows it in the list", async () => {
    const user = userEvent.setup();
    const seminar = makeSeminar();
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          id: "material-1",
          url: "https://example.com/slide.pdf",
          type: "slide",
        }),
        { status: 201 },
      ),
    );

    renderView({ seminars: [seminar] });

    await user.type(
      screen.getByPlaceholderText("資料のURL"),
      "https://example.com/slide.pdf",
    );
    await user.click(screen.getByRole("button", { name: "追加" }));

    expect(
      await screen.findByText("https://example.com/slide.pdf"),
    ).toBeInTheDocument();
  });

  it("shows an error and does not add a material when the URL is empty", async () => {
    const user = userEvent.setup();
    const seminar = makeSeminar();
    const fetchSpy = vi.spyOn(globalThis, "fetch");

    renderView({ seminars: [seminar] });
    await user.click(screen.getByRole("button", { name: "追加" }));

    expect(
      await screen.findByText("資料のURLを入力してください。"),
    ).toBeInTheDocument();
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("deletes a material", async () => {
    const user = userEvent.setup();
    const seminar = makeSeminar({
      materials: [
        {
          id: "material-1",
          url: "https://example.com/slide.pdf",
          type: "slide",
        },
      ],
    });
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(null, { status: 204 }),
    );

    renderView({ seminars: [seminar] });
    // 「削除」ボタンはゼミ本体の削除ボタンと、資料ごとの削除ボタンの両方に
    // 存在する。資料のものはDOM上で後(紹介資料セクション内)に来る。
    const deleteButtons = screen.getAllByRole("button", { name: "削除" });
    await user.click(deleteButtons[deleteButtons.length - 1]);

    await waitFor(() => {
      expect(
        screen.queryByText("https://example.com/slide.pdf"),
      ).not.toBeInTheDocument();
    });
  });
});
