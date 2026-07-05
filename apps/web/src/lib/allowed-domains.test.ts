import { describe, expect, it } from "vitest";
import { isEmailAllowed, parseAllowedDomains } from "@/lib/allowed-domains";

describe("parseAllowedDomains", () => {
  it("未指定・空は空配列", () => {
    expect(parseAllowedDomains(undefined)).toEqual([]);
    expect(parseAllowedDomains("")).toEqual([]);
  });

  it("カンマ区切りをtrim/小文字化して配列にする", () => {
    expect(parseAllowedDomains(" Stu.Musashino-u.ac.jp , gmail.com ")).toEqual([
      "stu.musashino-u.ac.jp",
      "gmail.com",
    ]);
  });
});

describe("isEmailAllowed", () => {
  const allow = ["stu.musashino-u.ac.jp"];

  it("許可リストが空なら全許可", () => {
    expect(isEmailAllowed("x@anywhere.com", [])).toBe(true);
  });

  it("ドメイン一致で許可(大文字も許容)", () => {
    expect(isEmailAllowed("Taro@Stu.Musashino-U.ac.jp", allow)).toBe(true);
  });

  it("ドメイン不一致で拒否", () => {
    expect(isEmailAllowed("taro@gmail.com", allow)).toBe(false);
  });

  it("emailが無い場合は拒否(許可リストありのとき)", () => {
    expect(isEmailAllowed(null, allow)).toBe(false);
    expect(isEmailAllowed(undefined, allow)).toBe(false);
  });
});
