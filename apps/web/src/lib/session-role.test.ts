import type { Session } from "next-auth";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("server-only", () => ({}));
// next-authのauth()はミドルウェアとしても使えるオーバーロード型を持ち、
// vi.mocked(auth)だとその型が誤って推論されるため、モック関数自体を
// 素のvi.fn()として型付けし直す。
const mockedAuth = vi.fn();
vi.mock("@/auth", () => ({
  auth: mockedAuth,
}));

const { getSessionRole } = await import("./session-role");

const session = { accessToken: "test-token" } as Session;

describe("getSessionRole", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("returns null when there is no session", async () => {
    mockedAuth.mockResolvedValue(null);

    expect(await getSessionRole()).toBeNull();
  });

  it("returns the role from /me on success", async () => {
    mockedAuth.mockResolvedValue(session);
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ role: "admin" }), { status: 200 }),
    );

    expect(await getSessionRole()).toBe("admin");
  });

  it("returns null when /me responds with an error status", async () => {
    mockedAuth.mockResolvedValue(session);
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(null, { status: 401 }),
    );

    expect(await getSessionRole()).toBeNull();
  });

  it("returns null when the request throws", async () => {
    mockedAuth.mockResolvedValue(session);
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("network"));

    expect(await getSessionRole()).toBeNull();
  });
});
