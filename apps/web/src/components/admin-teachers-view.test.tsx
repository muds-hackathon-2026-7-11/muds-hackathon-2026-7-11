import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useSession } from "next-auth/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AdminTeachersView, type AdminTeacher } from "./admin-teachers-view";

vi.mock("next-auth/react", () => ({
  useSession: vi.fn(),
}));

vi.mocked(useSession).mockReturnValue({
  data: null,
  status: "unauthenticated",
  update: vi.fn(),
});

function makeTeacher(overrides: Partial<AdminTeacher> = {}): AdminTeacher {
  return {
    id: "teacher-1",
    name: "山田先生",
    email: "yamada@example.com",
    research_theme: "機械学習",
    photo_url: null,
    is_active: true,
    ...overrides,
  };
}

describe("AdminTeachersView", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders teacher details", () => {
    render(<AdminTeachersView initialTeachers={[makeTeacher()]} />);

    expect(screen.getByText("山田先生")).toBeInTheDocument();
    expect(screen.getByText("yamada@example.com")).toBeInTheDocument();
    expect(screen.getByText("機械学習")).toBeInTheDocument();
  });

  it("edits a teacher's name and research theme", async () => {
    const user = userEvent.setup();
    const teacher = makeTeacher();
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ ...teacher, name: "新しい名前" }), {
        status: 200,
      }),
    );

    render(<AdminTeachersView initialTeachers={[teacher]} />);

    await user.click(screen.getByRole("button", { name: "編集" }));
    const nameInput = screen.getByDisplayValue("山田先生");
    await user.clear(nameInput);
    await user.type(nameInput, "新しい名前");
    await user.click(screen.getByRole("button", { name: "保存する" }));

    expect(await screen.findByText("新しい名前")).toBeInTheDocument();
  });

  it("deactivates a teacher via the is_active checkbox", async () => {
    const user = userEvent.setup();
    const teacher = makeTeacher();
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ ...teacher, is_active: false }), {
        status: 200,
      }),
    );

    render(<AdminTeachersView initialTeachers={[teacher]} />);

    await user.click(screen.getByRole("button", { name: "編集" }));
    await user.click(screen.getByRole("checkbox", { name: /有効/ }));
    await user.click(screen.getByRole("button", { name: "保存する" }));

    expect(await screen.findByText("(無効)")).toBeInTheDocument();
    expect(globalThis.fetch).toHaveBeenCalledWith(
      expect.stringContaining(`/admin/teachers/${teacher.id}`),
      expect.objectContaining({
        method: "PATCH",
        body: expect.stringContaining('"is_active":false'),
      }),
    );
  });

  it("shows an error when the name is cleared before saving", async () => {
    const user = userEvent.setup();
    const fetchSpy = vi.spyOn(globalThis, "fetch");

    render(<AdminTeachersView initialTeachers={[makeTeacher()]} />);

    await user.click(screen.getByRole("button", { name: "編集" }));
    await user.clear(screen.getByDisplayValue("山田先生"));
    await user.click(screen.getByRole("button", { name: "保存する" }));

    expect(
      await screen.findByText("名前を入力してください。"),
    ).toBeInTheDocument();
    expect(fetchSpy).not.toHaveBeenCalled();
  });
});
