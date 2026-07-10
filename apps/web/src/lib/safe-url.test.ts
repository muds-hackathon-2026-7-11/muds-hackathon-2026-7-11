import { describe, expect, it } from "vitest";
import { isSafeHttpUrl } from "./safe-url";

describe("isSafeHttpUrl", () => {
  it("accepts http URLs", () => {
    expect(isSafeHttpUrl("http://example.com/a.pdf")).toBe(true);
  });

  it("accepts https URLs", () => {
    expect(isSafeHttpUrl("https://example.com/a.pdf")).toBe(true);
  });

  it("rejects javascript: URLs", () => {
    expect(isSafeHttpUrl("javascript:alert(1)")).toBe(false);
  });

  it("rejects data: URLs", () => {
    expect(isSafeHttpUrl("data:text/html,<script>alert(1)</script>")).toBe(
      false,
    );
  });

  it("rejects unparseable strings", () => {
    expect(isSafeHttpUrl("not a url")).toBe(false);
  });

  it("rejects an empty string", () => {
    expect(isSafeHttpUrl("")).toBe(false);
  });
});
