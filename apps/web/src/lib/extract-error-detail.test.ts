import { describe, expect, it } from "vitest";
import { extractErrorDetail } from "@/lib/extract-error-detail";

function jsonResponse(body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status: 422,
    headers: { "Content-Type": "application/json" },
  });
}

describe("extractErrorDetail", () => {
  it("detailが文字列ならそのまま返す(HTTPException由来)", async () => {
    const res = jsonResponse({ detail: "既に管理者です。" });
    expect(await extractErrorDetail(res)).toBe("既に管理者です。");
  });

  it("detailがPydanticのバリデーションエラー配列なら、msgを連結して文字列化する", async () => {
    // FastAPI/Pydanticの422は detail: [{type, loc, msg, input, ctx}] という
    // オブジェクトの配列で返ってくる。これをそのままReactの子要素に渡すと
    // "Objects are not valid as a React child" で画面が落ちる(実際に発生した不具合)。
    const res = jsonResponse({
      detail: [
        {
          type: "value_error",
          loc: ["body", "url"],
          msg: "Value error, 資料URLはhttp(s)から始まるURLを入力してください。",
          input: "foo",
          ctx: { error: {} },
        },
      ],
    });
    expect(await extractErrorDetail(res)).toBe(
      "資料URLはhttp(s)から始まるURLを入力してください。",
    );
  });

  it("バリデーションエラーが複数件でも全て連結する", async () => {
    const res = jsonResponse({
      detail: [{ msg: "Value error, 1つ目のエラー" }, { msg: "2つ目のエラー" }],
    });
    expect(await extractErrorDetail(res)).toBe("1つ目のエラー\n2つ目のエラー");
  });

  it("specialCasesに一致するdetail文字列は読み替える", async () => {
    const res = jsonResponse({ detail: "TERM_CLOSED" });
    expect(
      await extractErrorDetail(res, { TERM_CLOSED: "締切を過ぎています。" }),
    ).toBe("締切を過ぎています。");
  });

  it("detailが無い・不正な形式ならフォールバックを返す", async () => {
    expect(await extractErrorDetail(jsonResponse({}))).toBe(
      "エラーが発生しました。",
    );
    expect(await extractErrorDetail(jsonResponse({ detail: 123 }))).toBe(
      "エラーが発生しました。",
    );
    expect(await extractErrorDetail(jsonResponse({ detail: [] }))).toBe(
      "エラーが発生しました。",
    );
  });

  it("JSONとして解釈できないレスポンスでもフォールバックを返す", async () => {
    const res = new Response("not json", { status: 500 });
    expect(await extractErrorDetail(res)).toBe("エラーが発生しました。");
  });
});
