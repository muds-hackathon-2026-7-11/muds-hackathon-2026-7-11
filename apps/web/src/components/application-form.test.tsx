import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { Session } from "next-auth";
import { useSession } from "next-auth/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  ApplicationForm,
  type ApplicationFormData,
  type Seminar,
} from "./application-form";

vi.mock("next-auth/react", () => ({
  useSession: vi.fn(),
}));

const seminars: Seminar[] = [
  { id: "sem-1", name: "福原ゼミ" },
  { id: "sem-2", name: "中村ゼミ" },
  { id: "sem-3", name: "岡ゼミ" },
];

function emptyDraft(
  overrides: Partial<ApplicationFormData> = {},
): ApplicationFormData {
  return {
    id: null,
    status: "draft",
    submitted_at: null,
    choices: [],
    is_editable: true,
    ...overrides,
  };
}

beforeEach(() => {
  vi.mocked(useSession).mockReturnValue({
    data: { accessToken: "test-token" } as Session,
    status: "authenticated",
    update: vi.fn(),
  } as ReturnType<typeof useSession>);
  // ゼミ未選択の志望理由はテスト間で共有されるjsdomのlocalStorageに
  // 一時保存されるため、前のテストの下書きが後続テストへ漏れないよう
  // 明示的にクリアする。
  window.localStorage.clear();
});

afterEach(() => {
  window.localStorage.clear();
  vi.restoreAllMocks();
});

describe("ApplicationForm", () => {
  it("renders three empty choice slots for a fresh draft", () => {
    render(
      <ApplicationForm seminars={seminars} initialApplication={emptyDraft()} />,
    );

    expect(screen.getByText("第1志望")).toBeInTheDocument();
    expect(screen.getByText("第2志望")).toBeInTheDocument();
    expect(screen.getByText("第3志望")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "提出する" }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "編集する" }),
    ).not.toBeInTheDocument();
  });

  it("shows a read-only view with an edit button when already submitted", () => {
    const submitted = emptyDraft({
      status: "submitted",
      submitted_at: "2026-07-01T00:00:00Z",
      choices: [
        {
          seminar_id: "sem-1",
          priority: 1,
          reason: "興味があるため",
          match_score: null,
          match_feedback: null,
        },
      ],
    });
    render(
      <ApplicationForm seminars={seminars} initialApplication={submitted} />,
    );

    expect(screen.getByText("福原ゼミ")).toBeInTheDocument();
    expect(screen.getByText("興味があるため")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "編集する" }),
    ).toBeInTheDocument();
    expect(screen.queryByRole("combobox")).not.toBeInTheDocument();
  });

  it("unlocks editing (with a revert button) when 編集する is clicked", async () => {
    const user = userEvent.setup();
    const submitted = emptyDraft({
      status: "submitted",
      submitted_at: "2026-07-01T00:00:00Z",
      choices: [
        {
          seminar_id: "sem-1",
          priority: 1,
          reason: "興味があるため",
          match_score: null,
          match_feedback: null,
        },
      ],
    });
    render(
      <ApplicationForm seminars={seminars} initialApplication={submitted} />,
    );

    await user.click(screen.getByRole("button", { name: "編集する" }));

    expect(screen.getByRole("button", { name: "戻る" })).toBeInTheDocument();
    expect(screen.getByDisplayValue("興味があるため")).toBeInTheDocument();
  });

  it("reverts to the read-only view locally when the autosave debounce hasn't fired yet", async () => {
    const user = userEvent.setup();
    const fetchSpy = vi.spyOn(globalThis, "fetch");
    const submitted = emptyDraft({
      status: "submitted",
      submitted_at: "2026-07-01T00:00:00Z",
      choices: [
        {
          seminar_id: "sem-1",
          priority: 1,
          reason: "興味があるため",
          match_score: null,
          match_feedback: null,
        },
      ],
    });
    render(
      <ApplicationForm seminars={seminars} initialApplication={submitted} />,
    );

    await user.click(screen.getByRole("button", { name: "編集する" }));
    const textarea = screen.getByDisplayValue("興味があるため");
    await user.clear(textarea);
    await user.type(textarea, "書き換え中");

    // 自動保存のデバウンス(1秒)が発火する前に戻るを押した場合、
    // サーバーには何も送られていないため、戻るはクライアント側だけで完結する。
    await user.click(screen.getByRole("button", { name: "戻る" }));

    expect(screen.getByText("興味があるため")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "編集する" }),
    ).toBeInTheDocument();
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("autosaves the input 1 second after typing stops", async () => {
    const user = userEvent.setup();
    const putResponse: ApplicationFormData = {
      id: "form-1",
      status: "draft",
      submitted_at: null,
      choices: [
        {
          seminar_id: "sem-1",
          priority: 1,
          reason: "興味があるため",
          match_score: null,
          match_feedback: null,
        },
      ],
      is_editable: true,
    };
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(
        new Response(JSON.stringify(putResponse), { status: 200 }),
      );

    render(
      <ApplicationForm seminars={seminars} initialApplication={emptyDraft()} />,
    );

    await user.selectOptions(screen.getAllByRole("combobox")[0], "sem-1");
    await user.type(
      screen.getAllByPlaceholderText(
        "このゼミを志望する理由を入力してください",
      )[0],
      "興味があるため",
    );

    // デバウンス中はまだ何も送られていない。
    expect(fetchSpy).not.toHaveBeenCalled();

    await waitFor(
      () => {
        expect(fetchSpy).toHaveBeenCalledTimes(1);
      },
      { timeout: 2000 },
    );
    const [url, init] = fetchSpy.mock.calls[0] as [string, RequestInit];
    expect(url).toContain("/applications/me");
    expect(init.method).toBe("PUT");
    await screen.findByText("保存済み");
  }, 10000);

  it("keeps an in-progress reason for a slot with no seminar selected after autosave", async () => {
    const user = userEvent.setup();
    const putResponse: ApplicationFormData = {
      id: "form-1",
      status: "draft",
      submitted_at: null,
      choices: [
        {
          seminar_id: "sem-1",
          priority: 1,
          reason: "1件目の理由",
          match_score: null,
          match_feedback: null,
        },
      ],
      is_editable: true,
    };
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify(putResponse), { status: 200 }),
    );

    render(
      <ApplicationForm seminars={seminars} initialApplication={emptyDraft()} />,
    );

    await user.selectOptions(screen.getAllByRole("combobox")[0], "sem-1");
    await user.type(
      screen.getAllByPlaceholderText(
        "このゼミを志望する理由を入力してください",
      )[0],
      "1件目の理由",
    );
    // 第2志望はゼミ未選択("選択してください")のまま理由だけ書きかける。
    await user.type(
      screen.getAllByPlaceholderText(
        "このゼミを志望する理由を入力してください",
      )[1],
      "2件目は検討中",
    );

    await screen.findByText("保存済み");

    // ゼミ未選択のスロットはPUTから除外されサーバー応答にも含まれないが、
    // 書きかけの理由がローカルで消えてはいけない。
    expect(screen.getByDisplayValue("2件目は検討中")).toBeInTheDocument();
  }, 10000);

  it("persists an orphan reason (no seminar selected) to localStorage and restores it after remounting", async () => {
    const user = userEvent.setup();

    const { unmount } = render(
      <ApplicationForm seminars={seminars} initialApplication={emptyDraft()} />,
    );

    // ゼミは選ばず、志望理由だけ書きかける。
    await user.type(
      screen.getAllByPlaceholderText(
        "このゼミを志望する理由を入力してください",
      )[0],
      "検討中です",
    );

    await waitFor(
      () => {
        expect(
          window.localStorage.getItem("application-form-local-draft"),
        ).toContain("検討中です");
      },
      { timeout: 2000 },
    );

    // ページを再読み込みした想定でアンマウント→再マウントする。
    unmount();
    render(
      <ApplicationForm seminars={seminars} initialApplication={emptyDraft()} />,
    );

    expect(screen.getByDisplayValue("検討中です")).toBeInTheDocument();
  }, 10000);

  it("does not autosave immediately on mount", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch");

    render(
      <ApplicationForm seminars={seminars} initialApplication={emptyDraft()} />,
    );
    await new Promise((resolve) => setTimeout(resolve, 1200));

    expect(fetchSpy).not.toHaveBeenCalled();
  }, 10000);

  it("limits the reason textarea to 400 characters and shows the counter", () => {
    render(
      <ApplicationForm seminars={seminars} initialApplication={emptyDraft()} />,
    );

    const textarea = screen.getAllByPlaceholderText(
      "このゼミを志望する理由を入力してください",
    )[0];
    expect(textarea).toHaveAttribute("maxLength", "400");
    expect(screen.getAllByText("0/400文字")[0]).toBeInTheDocument();
  });

  it("re-persists the snapshot to the server when reverting after a submit's PUT succeeded but POST failed", async () => {
    const user = userEvent.setup();
    const original: ApplicationFormData = {
      id: "form-1",
      status: "submitted",
      submitted_at: "2026-07-01T00:00:00Z",
      choices: [
        {
          seminar_id: "sem-1",
          priority: 1,
          reason: "興味があるため",
          match_score: null,
          match_feedback: null,
        },
      ],
      is_editable: true,
    };
    const putAfterEdit: ApplicationFormData = {
      ...original,
      choices: [{ ...original.choices[0], reason: "書き換え中" }],
    };
    const revertPutResponse: ApplicationFormData = original;

    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(
        new Response(JSON.stringify(putAfterEdit), { status: 200 }),
      ) // 提出するボタン: PUTは成功
      .mockResolvedValueOnce(new Response(null, { status: 500 })) // 提出するボタン: POSTは失敗
      .mockResolvedValueOnce(
        new Response(JSON.stringify(revertPutResponse), { status: 200 }),
      ); // 戻るボタン: 巻き戻しのPUT

    render(
      <ApplicationForm seminars={seminars} initialApplication={original} />,
    );

    await user.click(screen.getByRole("button", { name: "編集する" }));
    const textarea = screen.getByDisplayValue("興味があるため");
    await user.clear(textarea);
    await user.type(textarea, "書き換え中");
    await user.click(screen.getByRole("button", { name: "提出する" }));

    await waitFor(() => {
      expect(fetchSpy).toHaveBeenCalledTimes(2);
    });

    await user.click(screen.getByRole("button", { name: "戻る" }));

    await waitFor(() => {
      expect(screen.getByText("興味があるため")).toBeInTheDocument();
    });
    expect(
      screen.getByRole("button", { name: "編集する" }),
    ).toBeInTheDocument();

    expect(fetchSpy).toHaveBeenCalledTimes(3);
    const [url, init] = fetchSpy.mock.calls[2] as [string, RequestInit];
    expect(url).toContain("/applications/me");
    expect(init.method).toBe("PUT");
    const body = JSON.parse(init.body as string);
    expect(body.choices).toEqual([
      { seminar_id: "sem-1", priority: 1, reason: "興味があるため" },
    ]);
  });

  it("shows an error and does not call the API when no seminar is selected", async () => {
    const user = userEvent.setup();
    const fetchSpy = vi.spyOn(globalThis, "fetch");
    render(
      <ApplicationForm seminars={seminars} initialApplication={emptyDraft()} />,
    );

    await user.click(screen.getByRole("button", { name: "提出する" }));

    expect(
      await screen.findByText("志望を1件以上入力してください。"),
    ).toBeInTheDocument();
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("shows a friendly message when the term closed while the page was open", async () => {
    const user = userEvent.setup();
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(
        JSON.stringify({ detail: "現在募集中の期間がありません。" }),
        { status: 400 },
      ),
    );
    render(
      <ApplicationForm seminars={seminars} initialApplication={emptyDraft()} />,
    );

    await user.selectOptions(screen.getAllByRole("combobox")[0], "sem-1");
    await user.type(
      screen.getAllByPlaceholderText(
        "このゼミを志望する理由を入力してください",
      )[0],
      "興味があるため",
    );
    await user.click(screen.getByRole("button", { name: "提出する" }));

    expect(
      await screen.findByText("締切が過ぎました。ページを更新してください。"),
    ).toBeInTheDocument();
  });

  it("shows an error when a selected seminar has no reason", async () => {
    const user = userEvent.setup();
    render(
      <ApplicationForm seminars={seminars} initialApplication={emptyDraft()} />,
    );

    await user.selectOptions(screen.getAllByRole("combobox")[0], "sem-1");
    await user.click(screen.getByRole("button", { name: "提出する" }));

    expect(
      await screen.findByText("第1志望の志望理由が未入力です。"),
    ).toBeInTheDocument();
  });

  it("submits: PUT then POST, then shows the locked view with a success message", async () => {
    const user = userEvent.setup();
    const putResponse: ApplicationFormData = {
      id: "form-1",
      status: "draft",
      submitted_at: null,
      choices: [
        {
          seminar_id: "sem-1",
          priority: 1,
          reason: "興味があるため",
          match_score: null,
          match_feedback: null,
        },
      ],
      is_editable: true,
    };
    const postResponse: ApplicationFormData = {
      ...putResponse,
      status: "submitted",
      submitted_at: "2026-07-06T00:00:00Z",
    };

    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(
        new Response(JSON.stringify(putResponse), { status: 200 }),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify(postResponse), { status: 200 }),
      );

    render(
      <ApplicationForm seminars={seminars} initialApplication={emptyDraft()} />,
    );

    await user.selectOptions(screen.getAllByRole("combobox")[0], "sem-1");
    await user.type(
      screen.getAllByPlaceholderText(
        "このゼミを志望する理由を入力してください",
      )[0],
      "興味があるため",
    );
    await user.click(screen.getByRole("button", { name: "提出する" }));

    await screen.findByText("志望を提出しました。");
    expect(fetchSpy).toHaveBeenCalledTimes(2);

    const [firstUrl, firstInit] = fetchSpy.mock.calls[0] as [
      string,
      RequestInit,
    ];
    expect(firstUrl).toContain("/applications/me");
    expect(firstInit.method).toBe("PUT");

    const [secondUrl, secondInit] = fetchSpy.mock.calls[1] as [
      string,
      RequestInit,
    ];
    expect(secondUrl).toContain("/applications/me/submit");
    expect(secondInit.method).toBe("POST");

    expect(
      screen.getByRole("button", { name: "編集する" }),
    ).toBeInTheDocument();
  });

  it("shows a read-only view with no edit button and no inputs outside the recruitment period", () => {
    render(
      <ApplicationForm
        seminars={seminars}
        initialApplication={emptyDraft({ is_editable: false })}
      />,
    );

    expect(screen.getByText(/現在は募集期間外です/)).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "編集する" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "提出する" }),
    ).not.toBeInTheDocument();
    expect(screen.queryByRole("combobox")).not.toBeInTheDocument();
  });

  it("shows submitted choices read-only with no edit button when the recruitment period has closed", () => {
    const submittedPastPeriod = emptyDraft({
      status: "submitted",
      is_editable: false,
      submitted_at: "2026-07-01T00:00:00Z",
      choices: [
        {
          seminar_id: "sem-1",
          priority: 1,
          reason: "興味があるため",
          match_score: null,
          match_feedback: null,
        },
      ],
    });
    render(
      <ApplicationForm
        seminars={seminars}
        initialApplication={submittedPastPeriod}
      />,
    );

    expect(screen.getByText("福原ゼミ")).toBeInTheDocument();
    expect(screen.getByText("興味があるため")).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "編集する" }),
    ).not.toBeInTheDocument();
    expect(screen.queryByRole("combobox")).not.toBeInTheDocument();
  });

  it("excludes a seminar already selected in another slot from the other selects", async () => {
    const user = userEvent.setup();
    render(
      <ApplicationForm seminars={seminars} initialApplication={emptyDraft()} />,
    );

    const selects = screen.getAllByRole("combobox");
    await user.selectOptions(selects[0], "sem-1");

    const secondSelectOptions = within(selects[1]).getAllByRole("option");
    expect(
      secondSelectOptions.map((option) => (option as HTMLOptionElement).value),
    ).not.toContain("sem-1");
  });
});
