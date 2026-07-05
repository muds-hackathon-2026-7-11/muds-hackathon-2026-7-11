import type { Session } from "next-auth";
import { afterEach, describe, expect, it, vi } from "vitest";

// server-only はNext.jsのバンドラーが"react-server"条件でのみ無害化する
// マーカーパッケージで、素のNode/Vitestで実行すると常にthrowする実装になっている。
// テストではNext.jsのビルド環境を再現するためモック化する。
vi.mock("server-only", () => ({}));

const { serverApiFetch } = await import("./api-server");

const session = { accessToken: "test-token" } as Session;

describe("serverApiFetch", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.restoreAllMocks();
  });

  it("uses API_BASE_URL (Docker internal)", async () => {
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

    await serverApiFetch("/me", session);

    const [, init] = fetchSpy.mock.calls[0] as [string, RequestInit];
    const headers = new Headers(init.headers);
    expect(headers.get("Authorization")).toBe("Bearer test-token");
  });
});
