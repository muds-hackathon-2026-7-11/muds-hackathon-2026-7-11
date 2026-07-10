import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useSession } from "next-auth/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import {
  AdminRecruitmentTermsView,
  type AdminRecruitmentTerm,
  type AdminSeminarOption,
  type AdminSeminarRecruitment,
} from "./admin-recruitment-terms-view";

vi.mock("next-auth/react", () => ({
  useSession: vi.fn(),
}));

vi.mocked(useSession).mockReturnValue({
  data: null,
  status: "unauthenticated",
  update: vi.fn(),
});

function makeTerm(
  overrides: Partial<AdminRecruitmentTerm> = {},
): AdminRecruitmentTerm {
  return {
    id: "term-1",
    academic_year: 2027,
    starts_at: "2026-07-07",
    ends_at: "2027-04-03",
    status: "open",
    target_grades_summary: "未設定",
    ...overrides,
  };
}

function makeRecruitment(
  overrides: Partial<AdminSeminarRecruitment> = {},
): AdminSeminarRecruitment {
  return {
    seminar_id: "seminar-1",
    seminar_name: "AIゼミ",
    capacity: null,
    target_grades: null,
    ...overrides,
  };
}

type RenderOverrides = {
  terms?: AdminRecruitmentTerm[];
  seminars?: AdminSeminarOption[];
};

function renderView(overrides: RenderOverrides = {}) {
  return render(
    <AdminRecruitmentTermsView
      initialTerms={overrides.terms ?? []}
      allSeminars={overrides.seminars ?? []}
    />,
  );
}

// SkyDatePicker(自前カレンダー)で日付を選ぶ。ラベル("開始日"等)の
// ピッカーを開き、月ヘッダー("YYYY年 M月")を読みながら目的の月まで
// ‹/›で移動し、日をクリックする。現在日に依存せず決定的に動く。
async function pickDate(
  user: ReturnType<typeof userEvent.setup>,
  pickerLabel: string,
  value: string,
): Promise<void> {
  const [year, month, day] = value.split("-").map(Number);
  await user.click(screen.getByRole("button", { name: pickerLabel }));
  const dialog = screen.getByRole("dialog", { name: pickerLabel });

  // 目的の年月(target)まで前月/次月ボタンで移動する。
  const target = year * 12 + (month - 1);
  for (let guard = 0; guard < 240; guard++) {
    const header = dialog.querySelector("p")?.textContent ?? "";
    const m = /(\d+)年\s*(\d+)月/.exec(header);
    if (!m) {
      break;
    }
    const current = Number(m[1]) * 12 + (Number(m[2]) - 1);
    if (current === target) {
      break;
    }
    const label = current < target ? "次の月" : "前の月";
    await user.click(within(dialog).getByRole("button", { name: label }));
  }

  await user.click(within(dialog).getByRole("button", { name: String(day) }));
}

describe("AdminRecruitmentTermsView", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders existing terms with their period and status", () => {
    const term = makeTerm();
    renderView({ terms: [term] });

    expect(screen.getByText("2027年度")).toBeInTheDocument();
    expect(screen.getByText("募集中")).toBeInTheDocument();
  });

  it("shows the target-grades summary directly on the term card", () => {
    const term = makeTerm({ target_grades_summary: "B3, B4" });
    renderView({ terms: [term] });

    expect(screen.getByText("対象学年: B3, B4")).toBeInTheDocument();
  });

  it("shows 終了 when status is open but the end date has passed", () => {
    const term = makeTerm({
      starts_at: "2020-01-01",
      ends_at: "2020-01-31",
      status: "open",
    });
    renderView({ terms: [term] });

    expect(screen.getByText("終了")).toBeInTheDocument();
    expect(screen.queryByText("募集中")).not.toBeInTheDocument();
  });

  it("shows 準備中 as-is even though the start date is in the future", () => {
    const term = makeTerm({
      starts_at: "2999-01-01",
      ends_at: "2999-12-31",
      status: "preparing",
    });
    renderView({ terms: [term] });

    expect(screen.getByText("準備中")).toBeInTheDocument();
  });

  it("shows a message when there are no terms", () => {
    renderView();

    expect(
      screen.getByText("募集ラウンドがまだありません。"),
    ).toBeInTheDocument();
  });

  it("does not show the create form until the toggle button is clicked", async () => {
    const user = userEvent.setup();
    renderView();

    expect(screen.queryByPlaceholderText("2027")).not.toBeInTheDocument();

    await user.click(
      screen.getByRole("button", { name: "+ 新規募集ラウンドを作成" }),
    );
    expect(screen.getByPlaceholderText("2027")).toBeInTheDocument();
  });

  it("creates a new recruitment term (no bulk apply when there are no seminars)", async () => {
    const user = userEvent.setup();
    const created = makeTerm({
      id: "term-2",
      academic_year: 2028,
      status: "preparing",
    });
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(
        new Response(JSON.stringify(created), { status: 201 }),
      );

    renderView();

    await user.click(
      screen.getByRole("button", { name: "+ 新規募集ラウンドを作成" }),
    );
    // 年度欄はフォームを開いた時点で当年がプリセットされるため、
    // 一度クリアしてからテスト用の値を入力する。
    await user.clear(screen.getByPlaceholderText("2027"));
    await user.type(screen.getByPlaceholderText("2027"), "2028");
    await pickDate(user, "開始日", "2027-04-01");
    await pickDate(user, "終了日", "2028-03-31");
    await user.click(screen.getByRole("button", { name: "作成する" }));

    expect(await screen.findByText("2028年度")).toBeInTheDocument();
    expect(fetchSpy).toHaveBeenCalledTimes(1);
    expect(fetchSpy).toHaveBeenCalledWith(
      expect.stringContaining("/admin/recruitment-terms"),
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          academic_year: 2028,
          starts_at: "2027-04-01",
          ends_at: "2028-03-31",
          status: "preparing",
        }),
      }),
    );
  });

  it("shows an error when the academic year is missing", async () => {
    const user = userEvent.setup();
    const fetchSpy = vi.spyOn(globalThis, "fetch");

    renderView();

    await user.click(
      screen.getByRole("button", { name: "+ 新規募集ラウンドを作成" }),
    );
    // 年度は当年がプリセットされるので、空にしてバリデーションを確認する。
    await user.clear(screen.getByPlaceholderText("2027"));
    await user.click(screen.getByRole("button", { name: "作成する" }));

    expect(
      await screen.findByText("年度を入力してください。"),
    ).toBeInTheDocument();
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("edits a term's period and status", async () => {
    const user = userEvent.setup();
    const term = makeTerm({ status: "preparing" });
    const updated = { ...term, status: "open" as const };
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(
        new Response(JSON.stringify(updated), { status: 200 }),
      );

    renderView({ terms: [term] });

    await user.click(screen.getByRole("button", { name: "編集" }));
    // SkySelect(自前ドロップダウン)を開き、選択肢をクリックする。
    await user.click(screen.getByRole("button", { name: "状態" }));
    await user.click(
      within(screen.getByRole("listbox", { name: "状態" })).getByRole(
        "option",
        { name: "募集中" },
      ),
    );
    await user.click(screen.getByRole("button", { name: "保存する" }));

    await waitFor(() => {
      expect(fetchSpy).toHaveBeenCalledWith(
        expect.stringContaining(`/admin/recruitment-terms/${term.id}`),
        expect.objectContaining({
          method: "PATCH",
          body: JSON.stringify({
            starts_at: term.starts_at,
            ends_at: term.ends_at,
            status: "open",
          }),
        }),
      );
    });
    expect(await screen.findByText("募集中")).toBeInTheDocument();
  });

  it("does not have a delete button (deletion is a non-goal)", () => {
    const term = makeTerm();
    renderView({ terms: [term] });

    expect(
      screen.queryByRole("button", { name: "削除" }),
    ).not.toBeInTheDocument();
  });

  it("loads and shows per-seminar recruitment settings when 選択 is clicked", async () => {
    const user = userEvent.setup();
    const term = makeTerm();
    const recruitment = makeRecruitment({
      capacity: 10,
      target_grades: ["B1"],
    });
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify([recruitment]), { status: 200 }),
    );

    renderView({ terms: [term] });
    await user.click(screen.getByRole("button", { name: "ゼミ別設定" }));

    expect(await screen.findByText("AIゼミ")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("人数")).toHaveValue(10);
    expect(screen.getByRole("checkbox", { name: "B1" })).toBeChecked();
    expect(screen.getByRole("checkbox", { name: "B2" })).not.toBeChecked();
  });

  it("toggles the per-seminar settings closed when clicked again", async () => {
    const user = userEvent.setup();
    const term = makeTerm();
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify([makeRecruitment()]), { status: 200 }),
    );

    renderView({ terms: [term] });
    await user.click(screen.getByRole("button", { name: "ゼミ別設定" }));
    await screen.findByText("AIゼミ");

    await user.click(
      screen.getByRole("button", { name: "ゼミ別設定を閉じる" }),
    );
    expect(screen.queryByText("AIゼミ")).not.toBeInTheDocument();
  });

  it("saves capacity and target grades for a seminar in the selected term", async () => {
    const user = userEvent.setup();
    const term = makeTerm();
    const recruitment = makeRecruitment();
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(
        new Response(JSON.stringify([recruitment]), { status: 200 }),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            ...recruitment,
            capacity: 8,
            target_grades: ["B2", "B3", "B4"],
          }),
          { status: 200 },
        ),
      );

    renderView({ terms: [term] });
    await user.click(screen.getByRole("button", { name: "ゼミ別設定" }));
    await screen.findByText("AIゼミ");

    await user.type(screen.getByPlaceholderText("人数"), "8");
    // 未設定(null)は全学年チェック済みがデフォルトなので、B1を外す。
    await user.click(screen.getByRole("checkbox", { name: "B1" }));
    await user.click(screen.getByRole("button", { name: "保存する" }));

    await waitFor(() => {
      expect(fetchSpy).toHaveBeenCalledWith(
        expect.stringContaining(
          `/admin/recruitment-terms/${term.id}/seminars/${recruitment.seminar_id}`,
        ),
        expect.objectContaining({
          method: "PUT",
          body: JSON.stringify({
            capacity: 8,
            target_grades: ["B2", "B3", "B4"],
          }),
        }),
      );
    });
    // ラウンドのカード側の要約テキストにも、保存した対象学年が反映される。
    expect(
      await screen.findByText("対象学年: B2, B3, B4"),
    ).toBeInTheDocument();
  });

  it("asks for confirmation before saving with no grades selected", async () => {
    const user = userEvent.setup();
    const term = makeTerm();
    const recruitment = makeRecruitment({ target_grades: ["B1"] });
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);
    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(
        new Response(JSON.stringify([recruitment]), { status: 200 }),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({ ...recruitment, capacity: 8, target_grades: [] }),
          { status: 200 },
        ),
      );

    renderView({ terms: [term] });
    await user.click(screen.getByRole("button", { name: "ゼミ別設定" }));
    await screen.findByText("AIゼミ");

    await user.type(screen.getByPlaceholderText("人数"), "8");
    await user.click(screen.getByRole("checkbox", { name: "B1" }));
    await user.click(screen.getByRole("button", { name: "保存する" }));

    await waitFor(() => {
      expect(confirmSpy).toHaveBeenCalledWith(
        expect.stringContaining("AIゼミ"),
      );
    });
  });

  it("does not show the bulk target-grade section when there are no seminars", async () => {
    const user = userEvent.setup();
    renderView();

    await user.click(
      screen.getByRole("button", { name: "+ 新規募集ラウンドを作成" }),
    );

    expect(screen.queryByText("対象学年")).not.toBeInTheDocument();
  });

  it("bulk-applies the selected target grades to all seminars after creating a term", async () => {
    const user = userEvent.setup();
    const created = makeTerm({ id: "term-2", academic_year: 2028 });
    const seminars: AdminSeminarOption[] = [
      { id: "sem-1", name: "AIゼミ" },
      { id: "sem-2", name: "Webゼミ" },
    ];
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(
        new Response(JSON.stringify(created), { status: 201 }),
      )
      .mockResolvedValue(new Response(JSON.stringify({}), { status: 200 }));

    renderView({ seminars });

    await user.click(
      screen.getByRole("button", { name: "+ 新規募集ラウンドを作成" }),
    );
    await user.clear(screen.getByPlaceholderText("2027"));
    await user.type(screen.getByPlaceholderText("2027"), "2028");
    await pickDate(user, "開始日", "2027-04-01");
    await pickDate(user, "終了日", "2028-03-31");
    // B4(4年生)を対象外にする。
    await user.click(screen.getByRole("checkbox", { name: "B4" }));
    await user.click(screen.getByRole("button", { name: "作成する" }));

    await screen.findByText("2028年度");
    expect(
      await screen.findByText("対象学年: B1, B2, B3"),
    ).toBeInTheDocument();
    await waitFor(() => {
      expect(fetchSpy).toHaveBeenCalledTimes(3); // POST term + PUT x2 seminars
    });
    for (const seminar of seminars) {
      expect(fetchSpy).toHaveBeenCalledWith(
        expect.stringContaining(
          `/admin/recruitment-terms/${created.id}/seminars/${seminar.id}`,
        ),
        expect.objectContaining({
          method: "PUT",
          body: JSON.stringify({
            capacity: 10,
            target_grades: ["B1", "B2", "B3"],
          }),
        }),
      );
    }
  });

  it("shows an error when the bulk apply partially fails", async () => {
    const user = userEvent.setup();
    const created = makeTerm({ id: "term-2", academic_year: 2028 });
    const seminars: AdminSeminarOption[] = [
      { id: "sem-1", name: "AIゼミ" },
      { id: "sem-2", name: "Webゼミ" },
    ];
    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(
        new Response(JSON.stringify(created), { status: 201 }),
      )
      .mockResolvedValueOnce(new Response(JSON.stringify({}), { status: 200 }))
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ detail: "エラー" }), { status: 404 }),
      );

    renderView({ seminars });

    await user.click(
      screen.getByRole("button", { name: "+ 新規募集ラウンドを作成" }),
    );
    await user.clear(screen.getByPlaceholderText("2027"));
    await user.type(screen.getByPlaceholderText("2027"), "2028");
    await pickDate(user, "開始日", "2027-04-01");
    await pickDate(user, "終了日", "2028-03-31");
    await user.click(screen.getByRole("button", { name: "作成する" }));

    expect(
      await screen.findByText(/対象学年の一括設定に1件失敗しました/),
    ).toBeInTheDocument();
    // ラウンド自体の作成は成功しているので一覧には反映される。
    expect(screen.getByText("2028年度")).toBeInTheDocument();
  });
});
