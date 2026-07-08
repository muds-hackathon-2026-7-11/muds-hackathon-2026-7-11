import { render, screen, waitFor } from "@testing-library/react";
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

  it("shows the term's id for use in the assignment import CSV's term_id column", () => {
    const term = makeTerm({ id: "term-abc-123" });
    renderView({ terms: [term] });

    expect(screen.getByText("term-abc-123")).toBeInTheDocument();
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
    await user.type(screen.getByPlaceholderText("2027"), "2028");
    const dateInputs = screen.getAllByDisplayValue("");
    await user.type(dateInputs[0], "2027-04-01");
    await user.type(dateInputs[1], "2028-03-31");
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
    await user.selectOptions(screen.getByLabelText("状態"), "open");
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
    await user.type(screen.getByPlaceholderText("2027"), "2028");
    const dateInputs = screen.getAllByDisplayValue("");
    await user.type(dateInputs[0], "2027-04-01");
    await user.type(dateInputs[1], "2028-03-31");
    // B4(4年生)を対象外にする。
    await user.click(screen.getByRole("checkbox", { name: "B4" }));
    await user.click(screen.getByRole("button", { name: "作成する" }));

    await screen.findByText("2028年度");
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
    await user.type(screen.getByPlaceholderText("2027"), "2028");
    const dateInputs = screen.getAllByDisplayValue("");
    await user.type(dateInputs[0], "2027-04-01");
    await user.type(dateInputs[1], "2028-03-31");
    await user.click(screen.getByRole("button", { name: "作成する" }));

    expect(
      await screen.findByText(/対象学年の一括設定に1件失敗しました/),
    ).toBeInTheDocument();
    // ラウンド自体の作成は成功しているので一覧には反映される。
    expect(screen.getByText("2028年度")).toBeInTheDocument();
  });
});
