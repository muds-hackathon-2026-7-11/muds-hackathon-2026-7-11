import type { Session } from "next-auth";
import { afterEach, describe, expect, it, vi } from "vitest";
import { apiFetch } from "./api-client";

const session = { accessToken: "test-token" } as Session;

describe("apiFetch", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("falls back to the browser-reachable default URL", async () => {
    // NEXT_PUBLIC_API_URL はモジュール読み込み時に一度だけ評価される
    // (Next.jsのビルド時inlineと同じ挙動を再現するため)、未設定時のフォールバック
    // 値のみ検証できる。
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(new Response(null));

    await apiFetch("/me", session);

    expect(fetchSpy).toHaveBeenCalledWith(
      "http://localhost:8100/me",
      expect.anything(),
    );
  });

  it("attaches the session access token as a Bearer header", async () => {
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(new Response(null));

    await apiFetch("/me", session);

    const [, init] = fetchSpy.mock.calls[0] as [string, RequestInit];
    const headers = new Headers(init.headers);
    expect(headers.get("Authorization")).toBe("Bearer test-token");
  });

  it("omits the Authorization header when there is no session", async () => {
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(new Response(null));

    await apiFetch("/me", null);

    const [, init] = fetchSpy.mock.calls[0] as [string, RequestInit];
    const headers = new Headers(init.headers);
    expect(headers.get("Authorization")).toBeNull();
  });
});
