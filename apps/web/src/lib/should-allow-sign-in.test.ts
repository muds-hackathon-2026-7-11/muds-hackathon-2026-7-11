import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("./is-email-registered", () => ({
  isEmailRegistered: vi.fn(),
}));

const { isEmailRegistered } = await import("./is-email-registered");
const { shouldAllowSignIn } = await import("./should-allow-sign-in");

describe("shouldAllowSignIn", () => {
  afterEach(() => {
    vi.mocked(isEmailRegistered).mockReset();
  });

  it("rejects without checking registration when the domain is not allowed", async () => {
    const result = await shouldAllowSignIn("user@evil.example.com", [
      "stu.musashino-u.ac.jp",
    ]);

    expect(result).toBe(false);
    expect(isEmailRegistered).not.toHaveBeenCalled();
  });

  it("allows when the domain is allowed and the email is registered", async () => {
    vi.mocked(isEmailRegistered).mockResolvedValue(true);

    const result = await shouldAllowSignIn("s2622014@stu.musashino-u.ac.jp", [
      "stu.musashino-u.ac.jp",
    ]);

    expect(result).toBe(true);
    expect(isEmailRegistered).toHaveBeenCalledWith(
      "s2622014@stu.musashino-u.ac.jp",
    );
  });

  it("rejects when the domain is allowed but the email is not registered", async () => {
    vi.mocked(isEmailRegistered).mockResolvedValue(false);

    const result = await shouldAllowSignIn("nobody@stu.musashino-u.ac.jp", [
      "stu.musashino-u.ac.jp",
    ]);

    expect(result).toBe(false);
  });

  it("checks registration for any domain when no domain restriction is set", async () => {
    vi.mocked(isEmailRegistered).mockResolvedValue(true);

    const result = await shouldAllowSignIn("teacher@gmail.com", []);

    expect(result).toBe(true);
    expect(isEmailRegistered).toHaveBeenCalledWith("teacher@gmail.com");
  });
});
