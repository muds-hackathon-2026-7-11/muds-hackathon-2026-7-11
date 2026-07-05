import type { Session } from "next-auth";
import { afterEach, describe, expect, it, vi } from "vitest";
import { apiFetch, serverApiFetch } from "./api";

const session = { accessToken: "test-token" } as Session;

describe("apiFetch / serverApiFetch", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.restoreAllMocks();
  });

  it("apiFetch falls back to the browser-reachable default URL", async () => {
    // NEXT_PUBLIC_API_URL はモジュール読み込み時に一度だけ評価される
    // (Next.jsのビルド時inlineと同じ挙動を再現するため)。そのためテストでは
    // vi.stubEnv は効かず、未設定時のフォールバック値のみ検証できる。
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(new Response(null));

    await apiFetch("/me", session);

    expect(fetchSpy).toHaveBeenCalledWith(
      "http://localhost:8100/me",
      expect.anything(),
    );
  });

  it("serverApiFetch uses API_BASE_URL (Docker internal)", async () => {
    vi.stubEnv("API_BASE_URL", "http://api:8000");
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(new Response(null));

    await serverApiFetch("/me", session);

    expect(fetchSpy).toHaveBeenCalledWith(
      "http://api:8000/me",
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
