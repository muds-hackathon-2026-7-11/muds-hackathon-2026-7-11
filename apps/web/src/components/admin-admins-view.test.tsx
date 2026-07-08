import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useSession } from "next-auth/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AdminAdminsView, type AdminUser } from "./admin-admins-view";

vi.mock("next-auth/react", () => ({
  useSession: vi.fn(),
}));

vi.mocked(useSession).mockReturnValue({
  data: null,
  status: "unauthenticated",
  update: vi.fn(),
});

function makeAdmin(overrides: Partial<AdminUser> = {}): AdminUser {
  return {
    id: "admin-1",
    name: "橘 由翔",
    email: "admin@example.com",
    is_active: true,
    ...overrides,
  };
}

describe("AdminAdminsView", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders admin details", () => {
    render(<AdminAdminsView initialAdmins={[makeAdmin()]} />);

    expect(screen.getByText("橘 由翔")).toBeInTheDocument();
    expect(screen.getByText("admin@example.com")).toBeInTheDocument();
  });

  it("shows a message when there are no admins", () => {
    render(<AdminAdminsView initialAdmins={[]} />);

    expect(screen.getByText("管理者がまだいません。")).toBeInTheDocument();
  });

  it("looks up a candidate by email, shows their name, and adds them on confirmation", async () => {
    const user = userEvent.setup();
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            id: "teacher-1",
            name: "新任先生",
            email: "new-admin@example.com",
            role: "teacher",
          }),
          { status: 200 },
        ),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify(
            makeAdmin({
              id: "teacher-1",
              name: "新任先生",
              email: "new-admin@example.com",
            }),
          ),
          { status: 201 },
        ),
      );

    render(<AdminAdminsView initialAdmins={[]} />);

    await user.click(screen.getByRole("button", { name: "+ 管理者を追加" }));
    await user.type(
      screen.getByPlaceholderText("メールアドレス"),
      "new-admin@example.com",
    );
    await user.click(screen.getByRole("button", { name: "確認する" }));

    expect(await screen.findByText("新任先生")).toBeInTheDocument();
    expect(fetchSpy).toHaveBeenNthCalledWith(
      1,
      expect.stringContaining(
        "/admin/admins/lookup?email=new-admin%40example.com",
      ),
      expect.anything(),
    );

    await user.click(screen.getByRole("button", { name: "この人を追加する" }));

    expect(await screen.findAllByText("新任先生")).not.toHaveLength(0);
    expect(fetchSpy).toHaveBeenNthCalledWith(
      2,
      expect.stringContaining("/admin/admins"),
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ email: "new-admin@example.com" }),
      }),
    );
  });

  it("shows an invalid-email style error when the lookup finds no user", async () => {
    const user = userEvent.setup();
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ detail: "not found" }), { status: 404 }),
    );

    render(<AdminAdminsView initialAdmins={[]} />);

    await user.click(screen.getByRole("button", { name: "+ 管理者を追加" }));
    await user.type(
      screen.getByPlaceholderText("メールアドレス"),
      "unknown@example.com",
    );
    await user.click(screen.getByRole("button", { name: "確認する" }));

    expect(
      await screen.findByText(
        "無効なメールアドレスです(登録されているユーザーが見つかりません)。",
      ),
    ).toBeInTheDocument();
  });

  it("shows an error when confirming without entering an email", async () => {
    const user = userEvent.setup();
    const fetchSpy = vi.spyOn(globalThis, "fetch");

    render(<AdminAdminsView initialAdmins={[]} />);

    await user.click(screen.getByRole("button", { name: "+ 管理者を追加" }));
    await user.click(screen.getByRole("button", { name: "確認する" }));

    expect(
      await screen.findByText("メールアドレスを入力してください。"),
    ).toBeInTheDocument();
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("removes an admin from the list after confirmation", async () => {
    const user = userEvent.setup();
    const admin = makeAdmin();
    vi.spyOn(window, "confirm").mockReturnValue(true);
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(new Response(null, { status: 204 }));

    render(<AdminAdminsView initialAdmins={[admin]} />);

    await user.click(screen.getByRole("button", { name: "削除" }));

    expect(
      await screen.findByText("管理者がまだいません。"),
    ).toBeInTheDocument();
    expect(fetchSpy).toHaveBeenCalledWith(
      expect.stringContaining(`/admin/admins/${admin.id}`),
      expect.objectContaining({ method: "DELETE" }),
    );
  });

  it("does not remove an admin when the confirmation is cancelled", async () => {
    const user = userEvent.setup();
    const admin = makeAdmin();
    vi.spyOn(window, "confirm").mockReturnValue(false);
    const fetchSpy = vi.spyOn(globalThis, "fetch");

    render(<AdminAdminsView initialAdmins={[admin]} />);

    await user.click(screen.getByRole("button", { name: "削除" }));

    expect(fetchSpy).not.toHaveBeenCalled();
    expect(screen.getByText("橘 由翔")).toBeInTheDocument();
  });

  it("shows the error message when removal fails (e.g. self-removal)", async () => {
    const user = userEvent.setup();
    const admin = makeAdmin();
    vi.spyOn(window, "confirm").mockReturnValue(true);
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ detail: "自分自身は解除できません。" }), {
        status: 403,
      }),
    );

    render(<AdminAdminsView initialAdmins={[admin]} />);
    await user.click(screen.getByRole("button", { name: "削除" }));

    expect(
      await screen.findByText("自分自身は解除できません。"),
    ).toBeInTheDocument();
    expect(screen.getByText("橘 由翔")).toBeInTheDocument();
  });
});
