import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { signIn } from "next-auth/react";
import { describe, expect, it, vi } from "vitest";
import { LoginButton } from "./login-button";

vi.mock("next-auth/react", () => ({
  signIn: vi.fn(),
}));

describe("LoginButton", () => {
  it('calls signIn("google") when clicked', async () => {
    const user = userEvent.setup();
    render(<LoginButton />);

    await user.click(screen.getByRole("button", { name: "Googleでログイン" }));

    expect(signIn).toHaveBeenCalledWith("google");
  });
});
