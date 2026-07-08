import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { usePathname } from "next/navigation";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { MenuBar } from "./menu-bar";

vi.mock("next/navigation", () => ({
  usePathname: vi.fn(),
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

  it("does not show the admin nav item for non-admins", () => {
    render(<MenuBar isAdmin={false} />);

    expect(
      screen.queryByRole("link", { name: "管理者" }),
    ).not.toBeInTheDocument();
  });

  it("shows the admin nav item for admins", () => {
    render(<MenuBar isAdmin={true} />);

    expect(screen.getByRole("link", { name: "管理者" })).toHaveAttribute(
      "href",
      "/admin",
    );
  });

  it("renders the settings button as disabled", () => {
    render(<MenuBar isAdmin={false} />);

    expect(screen.getByRole("button", { name: "設定(準備中)" })).toBeDisabled();
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
