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
  });

  it("edits a teacher's email", async () => {
    const user = userEvent.setup();
    const teacher = makeTeacher();
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(
        new Response(
          JSON.stringify({ ...teacher, email: "new-email@example.com" }),
          { status: 200 },
        ),
      );

    render(<AdminTeachersView initialTeachers={[teacher]} />);

    await user.click(screen.getByRole("button", { name: "編集" }));
    const emailInput = screen.getByDisplayValue("yamada@example.com");
    await user.clear(emailInput);
    await user.type(emailInput, "new-email@example.com");
    await user.click(screen.getByRole("button", { name: "保存する" }));

    expect(
      await screen.findByText("new-email@example.com"),
    ).toBeInTheDocument();
    expect(fetchSpy).toHaveBeenCalledWith(
      expect.stringContaining(`/admin/teachers/${teacher.id}`),
      expect.objectContaining({
        method: "PATCH",
        body: expect.stringContaining('"email":"new-email@example.com"'),
      }),
    );
  });

  it("edits a teacher's name", async () => {
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

  it("adds a new teacher", async () => {
    const user = userEvent.setup();
    const created = makeTeacher({
      id: "teacher-2",
      name: "新任先生",
      email: "new@example.com",
    });
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(
        new Response(JSON.stringify(created), { status: 201 }),
      );

    render(<AdminTeachersView initialTeachers={[]} />);

    await user.click(screen.getByRole("button", { name: "+ 教員を追加" }));
    await user.type(screen.getByPlaceholderText("名前"), "新任先生");
    await user.type(
      screen.getByPlaceholderText("メールアドレス"),
      "new@example.com",
    );
    await user.click(screen.getByRole("button", { name: "追加する" }));

    expect(await screen.findByText("新任先生")).toBeInTheDocument();
    expect(fetchSpy).toHaveBeenCalledWith(
      expect.stringContaining("/admin/teachers"),
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ name: "新任先生", email: "new@example.com" }),
      }),
    );
  });

  it("shows an error when adding a teacher without a name or email", async () => {
    const user = userEvent.setup();
    const fetchSpy = vi.spyOn(globalThis, "fetch");

    render(<AdminTeachersView initialTeachers={[]} />);

    await user.click(screen.getByRole("button", { name: "+ 教員を追加" }));
    await user.click(screen.getByRole("button", { name: "追加する" }));

    expect(
      await screen.findByText("名前とメールアドレスを入力してください。"),
    ).toBeInTheDocument();
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("deletes (deactivates) a teacher after confirmation", async () => {
    const user = userEvent.setup();
    const teacher = makeTeacher();
    vi.spyOn(window, "confirm").mockReturnValue(true);
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(new Response(null, { status: 204 }));

    render(<AdminTeachersView initialTeachers={[teacher]} />);

    await user.click(screen.getByRole("button", { name: "削除" }));

    expect(await screen.findByText("(無効)")).toBeInTheDocument();
    expect(fetchSpy).toHaveBeenCalledWith(
      expect.stringContaining(`/admin/teachers/${teacher.id}`),
      expect.objectContaining({ method: "DELETE" }),
    );
  });

  it("does not delete a teacher when the confirmation is cancelled", async () => {
    const user = userEvent.setup();
    const teacher = makeTeacher();
    vi.spyOn(window, "confirm").mockReturnValue(false);
    const fetchSpy = vi.spyOn(globalThis, "fetch");

    render(<AdminTeachersView initialTeachers={[teacher]} />);

    await user.click(screen.getByRole("button", { name: "削除" }));

    expect(fetchSpy).not.toHaveBeenCalled();
    expect(screen.queryByText("(無効)")).not.toBeInTheDocument();
  });

  it("shows an error when the name and email are cleared before saving", async () => {
    const user = userEvent.setup();
    const fetchSpy = vi.spyOn(globalThis, "fetch");

    render(<AdminTeachersView initialTeachers={[makeTeacher()]} />);

    await user.click(screen.getByRole("button", { name: "編集" }));
    await user.clear(screen.getByDisplayValue("山田先生"));
    await user.click(screen.getByRole("button", { name: "保存する" }));

    expect(
      await screen.findByText("名前とメールアドレスを入力してください。"),
    ).toBeInTheDocument();
    expect(fetchSpy).not.toHaveBeenCalled();
  });
});
