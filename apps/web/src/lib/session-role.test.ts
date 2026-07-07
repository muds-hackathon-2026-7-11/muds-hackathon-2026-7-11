import type { Session } from "next-auth";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("server-only", () => ({}));

const { getSessionRole } = await import("./session-role");

const session = { accessToken: "test-token" } as Session;

describe("getSessionRole", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("returns null when there is no session", async () => {
    expect(await getSessionRole(null)).toBeNull();
  });

  it("returns the role from /me on success", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ role: "admin" }), { status: 200 }),
    );

    expect(await getSessionRole(session)).toBe("admin");
  });

  it("returns null when /me responds with an error status", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(null, { status: 401 }),
    );

    expect(await getSessionRole(session)).toBeNull();
  });

  it("returns null when the request throws", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("network"));

    expect(await getSessionRole(session)).toBeNull();
  });
});
