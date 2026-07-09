import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { usePathname } from "next/navigation";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { MenuBar } from "./menu-bar";

vi.mock("next/navigation", () => ({
  usePathname: vi.fn(),
}));

vi.mock("next-auth/react", () => ({
  signOut: vi.fn(),
}));

describe("MenuBar", () => {
  beforeEach(() => {
    vi.mocked(usePathname).mockReturnValue("/");
  });

  it("renders the logo and nav items with correct links", () => {
    render(<MenuBar isAdmin={false} isTeacher={false} />);

    expect(screen.getByRole("link", { name: "Zemi-Match" })).toHaveAttribute(
      "href",
      "/",
    );
    expect(screen.getByRole("link", { name: "マイページ" })).toHaveAttribute(
      "href",
      "/",
    );
    expect(screen.getByRole("link", { name: "応募状況" })).toHaveAttribute(
      "href",
      "/assignment",
    );
    expect(screen.getByRole("link", { name: "AIゼミ相談" })).toHaveAttribute(
      "href",
      "/chat",
    );
  });

  it("does not show the applicants link for non-teachers", () => {
    render(<MenuBar isAdmin={false} isTeacher={false} />);

    expect(
      screen.queryByRole("link", { name: "応募者一覧" }),
    ).not.toBeInTheDocument();
  });

  it("shows the applicants link for teachers", () => {
    render(<MenuBar isAdmin={false} isTeacher={true} />);

    expect(screen.getByRole("link", { name: "応募者一覧" })).toHaveAttribute(
      "href",
      "/teacher/applicants",
    );
  });

  it("marks the current page as active", () => {
    vi.mocked(usePathname).mockReturnValue("/assignment");
    render(<MenuBar isAdmin={false} isTeacher={false} />);

    expect(screen.getByRole("link", { name: "応募状況" })).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(
      screen.getByRole("link", { name: "マイページ" }),
    ).not.toHaveAttribute("aria-current");
  });

  it("does not show the admin link in the settings menu for non-admins", async () => {
    const user = userEvent.setup();
    render(<MenuBar isAdmin={false} isTeacher={false} />);

    await user.click(screen.getByRole("button", { name: "設定" }));

    expect(
      screen.queryByRole("link", { name: /管理者/ }),
    ).not.toBeInTheDocument();
    // ログアウトは管理者かどうかに関わらず出る。
    expect(
      screen.getByRole("button", { name: "ログアウト" }),
    ).toBeInTheDocument();
  });

  it("shows the admin link in the settings menu for admins", async () => {
    const user = userEvent.setup();
    render(<MenuBar isAdmin={true} isTeacher={false} />);

    await user.click(screen.getByRole("button", { name: "設定" }));

    expect(screen.getByRole("link", { name: /管理者/ })).toHaveAttribute(
      "href",
      "/admin",
    );
  });

  it("opens the settings menu with a logout option when the gear is clicked", async () => {
    const user = userEvent.setup();
    render(<MenuBar isAdmin={false} isTeacher={false} />);

    // 初期状態ではログアウトは表示されていない。
    expect(
      screen.queryByRole("button", { name: "ログアウト" }),
    ).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "設定" }));

    expect(
      screen.getByRole("button", { name: "ログアウト" }),
    ).toBeInTheDocument();
  });

  it("toggles the mobile menu open and closed", async () => {
    const user = userEvent.setup();
    render(<MenuBar isAdmin={false} isTeacher={false} />);

    const toggle = screen.getByRole("button", { name: "メニューを開閉する" });
    expect(toggle).toHaveAttribute("aria-expanded", "false");

    await user.click(toggle);
    expect(toggle).toHaveAttribute("aria-expanded", "true");

    await user.click(toggle);
    expect(toggle).toHaveAttribute("aria-expanded", "false");
  });

  it("shows logout inside the mobile menu", async () => {
    const user = userEvent.setup();
    render(<MenuBar isAdmin={false} isTeacher={false} />);

    // メニューを開く前はログアウトは出ていない。
    expect(
      screen.queryByRole("button", { name: "ログアウト" }),
    ).not.toBeInTheDocument();

    await user.click(
      screen.getByRole("button", { name: "メニューを開閉する" }),
    );

    expect(
      screen.getByRole("button", { name: "ログアウト" }),
    ).toBeInTheDocument();
  });

  it("shows the admin link inside the mobile menu for admins", async () => {
    const user = userEvent.setup();
    render(<MenuBar isAdmin={true} isTeacher={false} />);

    await user.click(
      screen.getByRole("button", { name: "メニューを開閉する" }),
    );

    const adminLinks = screen.getAllByRole("link", { name: /管理者/ });
    expect(adminLinks[adminLinks.length - 1]).toHaveAttribute("href", "/admin");
  });

  it("closes the mobile menu after selecting a nav item", async () => {
    const user = userEvent.setup();
    render(<MenuBar isAdmin={false} isTeacher={false} />);

    const toggle = screen.getByRole("button", { name: "メニューを開閉する" });
    await user.click(toggle);

    const mobileLinks = screen.getAllByRole("link", { name: "応募状況" });
    await user.click(mobileLinks[mobileLinks.length - 1]);

    expect(toggle).toHaveAttribute("aria-expanded", "false");
  });
});
