import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("server-only", () => ({}));

const { isEmailRegistered } = await import("./is-email-registered");

describe("isEmailRegistered", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("returns true when the API reports the email exists", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ exists: true }), { status: 200 }),
    );

    expect(await isEmailRegistered("known@example.com")).toBe(true);
  });

  it("returns false when the API reports the email is unknown", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ exists: false }), { status: 200 }),
    );

    expect(await isEmailRegistered("unknown@example.com")).toBe(false);
  });

  it("fails closed (false) when the API request fails", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("network error"));

    expect(await isEmailRegistered("known@example.com")).toBe(false);
  });

  it("fails closed (false) when the API returns a non-ok response", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(null, { status: 500 }),
    );

    expect(await isEmailRegistered("known@example.com")).toBe(false);
  });

  it("returns false without calling the API when email is missing", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch");

    expect(await isEmailRegistered(null)).toBe(false);
    expect(await isEmailRegistered(undefined)).toBe(false);
    expect(fetchSpy).not.toHaveBeenCalled();
  });
});
