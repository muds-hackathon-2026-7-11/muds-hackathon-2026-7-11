import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { signIn } from "next-auth/react";
import { describe, expect, it, vi } from "vitest";
import LoginPage from "./page";

vi.mock("next-auth/react", () => ({
  signIn: vi.fn(),
}));

describe("LoginPage", () => {
  it('calls signIn("google") when the button is clicked', async () => {
    const user = userEvent.setup();
    render(<LoginPage />);

    await user.click(screen.getByRole("button", { name: "Googleでログイン" }));

    expect(signIn).toHaveBeenCalledWith("google");
  });
});
