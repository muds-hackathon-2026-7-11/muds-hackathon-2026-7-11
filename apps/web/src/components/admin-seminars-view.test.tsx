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

describe("AdminSeminarsView", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders existing seminars and their assigned teachers", () => {
    const teacher = makeTeacher();
    const seminar = makeSeminar({
      teachers: [{ id: teacher.id, name: teacher.name }],
    });
    render(
      <AdminSeminarsView
        initialSeminars={[seminar]}
        teacherOptions={[teacher]}
      />,
    );

    expect(screen.getByText("AIゼミ")).toBeInTheDocument();
    const checkbox = screen.getByRole("checkbox", { name: /山田先生/ });
    expect(checkbox).toBeChecked();
  });

  it("creates a new seminar and shows it in the list", async () => {
    const user = userEvent.setup();
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          id: "seminar-2",
          name: "新ゼミ",
          description: null,
          photo_url: null,
          teachers: [],
        }),
        { status: 201 },
      ),
    );

    render(<AdminSeminarsView initialSeminars={[]} teacherOptions={[]} />);

    await user.type(screen.getByPlaceholderText("ゼミ名"), "新ゼミ");
    await user.click(screen.getByRole("button", { name: "作成する" }));

    expect(await screen.findByText("新ゼミ")).toBeInTheDocument();
  });

  it("shows an error and does not add a seminar when the name is empty", async () => {
    const user = userEvent.setup();
    const fetchSpy = vi.spyOn(globalThis, "fetch");

    render(<AdminSeminarsView initialSeminars={[]} teacherOptions={[]} />);
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

    render(
      <AdminSeminarsView initialSeminars={[seminar]} teacherOptions={[]} />,
    );

    await user.click(screen.getByRole("button", { name: "編集" }));
    const nameInput = screen.getByDisplayValue("AIゼミ");
    await user.clear(nameInput);
    await user.type(nameInput, "改名後");
    await user.click(screen.getByRole("button", { name: "保存する" }));

    expect(await screen.findByText("改名後")).toBeInTheDocument();
  });

  it("removes a seminar after confirming deletion", async () => {
    const user = userEvent.setup();
    const seminar = makeSeminar();
    vi.spyOn(window, "confirm").mockReturnValue(true);
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(null, { status: 204 }),
    );

    render(
      <AdminSeminarsView initialSeminars={[seminar]} teacherOptions={[]} />,
    );
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

    render(
      <AdminSeminarsView initialSeminars={[seminar]} teacherOptions={[]} />,
    );
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

    render(
      <AdminSeminarsView
        initialSeminars={[seminar]}
        teacherOptions={[teacher]}
      />,
    );

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
});
