import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { usePathname } from "next/navigation";
import { signOut } from "next-auth/react";
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
    render(<MenuBar isAdmin={false} />);

    expect(screen.getByRole("link", { name: "Zemi-Match" })).toHaveAttribute(
      "href",
      "/",
    );
    expect(screen.getByRole("link", { name: "マイページ" })).toHaveAttribute(
      "href",
      "/",
    );
    expect(screen.getByRole("link", { name: "志望状況一覧" })).toHaveAttribute(
      "href",
      "/assignment",
    );
  });

  it("marks the current page as active", () => {
    vi.mocked(usePathname).mockReturnValue("/assignment");
    render(<MenuBar isAdmin={false} />);

    expect(screen.getByRole("link", { name: "志望状況一覧" })).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(
      screen.getByRole("link", { name: "マイページ" }),
    ).not.toHaveAttribute("aria-current");
  });

  it("links the chat button to the AI seminar chat page", () => {
    render(<MenuBar isAdmin={false} />);

    expect(screen.getByRole("link", { name: "AIゼミ相談" })).toHaveAttribute(
      "href",
      "/chat",
    );
  });

  it("opens the settings dropdown and shows ログアウト but not 管理者画面 for non-admins", async () => {
    const user = userEvent.setup();
    render(<MenuBar isAdmin={false} />);

    expect(screen.queryByText("ログアウト")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "設定" }));

    expect(screen.getByText("ログアウト")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "管理者画面" })).not.toBeInTheDocument();
  });

  it("shows 管理者画面 in the settings dropdown for admins", async () => {
    const user = userEvent.setup();
    render(<MenuBar isAdmin={true} />);

    await user.click(screen.getByRole("button", { name: "設定" }));

    expect(screen.getByRole("link", { name: "管理者画面" })).toHaveAttribute(
      "href",
      "/admin",
    );
  });

  it("calls signOut when ログアウト is clicked", async () => {
    const user = userEvent.setup();
    render(<MenuBar isAdmin={false} />);

    await user.click(screen.getByRole("button", { name: "設定" }));
    await user.click(screen.getByRole("button", { name: "ログアウト" }));

    expect(signOut).toHaveBeenCalled();
  });

  it("closes the settings dropdown when clicking outside", async () => {
    const user = userEvent.setup();
    render(<MenuBar isAdmin={false} />);

    await user.click(screen.getByRole("button", { name: "設定" }));
    expect(screen.getByText("ログアウト")).toBeInTheDocument();

    await user.click(document.body);
    expect(screen.queryByText("ログアウト")).not.toBeInTheDocument();
  });

  it("toggles the mobile menu open and closed", async () => {
    const user = userEvent.setup();
    render(<MenuBar isAdmin={false} />);

    const toggle = screen.getByRole("button", { name: "メニューを開閉する" });
    expect(toggle).toHaveAttribute("aria-expanded", "false");

    await user.click(toggle);
    expect(toggle).toHaveAttribute("aria-expanded", "true");

    await user.click(toggle);
    expect(toggle).toHaveAttribute("aria-expanded", "false");
  });

  it("closes the mobile menu after selecting a nav item", async () => {
    const user = userEvent.setup();
    render(<MenuBar isAdmin={false} />);

    const toggle = screen.getByRole("button", { name: "メニューを開閉する" });
    await user.click(toggle);

    const mobileLinks = screen.getAllByRole("link", { name: "志望状況一覧" });
    await user.click(mobileLinks[mobileLinks.length - 1]);

    expect(toggle).toHaveAttribute("aria-expanded", "false");
  });
});
