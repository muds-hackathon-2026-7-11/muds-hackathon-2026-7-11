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
  window.localStorage.clear();
});

afterEach(() => {
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

  it("reverts to the read-only view without calling the API when nothing was ever sent to the server", async () => {
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

    await user.click(screen.getByRole("button", { name: "戻る" }));

    expect(screen.getByText("興味があるため")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "編集する" }),
    ).toBeInTheDocument();
    // 編集中は自動保存しないため、通常の戻るはクライアント側だけで完結し、
    // APIを呼ばない(毎回PUTすると提出日時が更新される副作用があるため)。
    expect(fetchSpy).not.toHaveBeenCalled();
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

  it("shows a warning and disables submit outside the recruitment period, but keeps inputs editable", () => {
    render(
      <ApplicationForm
        seminars={seminars}
        initialApplication={emptyDraft({ is_editable: false })}
      />,
    );

    expect(screen.getByText(/現在は募集期間外です/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "提出する" })).toBeDisabled();
    expect(screen.getAllByRole("combobox")[0]).not.toBeDisabled();
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

  it("auto-saves to localStorage outside the recruitment period", async () => {
    const user = userEvent.setup();
    render(
      <ApplicationForm
        seminars={seminars}
        initialApplication={emptyDraft({ is_editable: false })}
      />,
    );

    await user.selectOptions(screen.getAllByRole("combobox")[0], "sem-1");

    await waitFor(
      () => {
        const raw = window.localStorage.getItem("application-form-local-draft");
        expect(raw).not.toBeNull();
        expect(JSON.parse(raw ?? "[]")[0].seminarId).toBe("sem-1");
      },
      { timeout: 2000 },
    );
  });

  it("does not let a stale localStorage draft override an already-submitted application", () => {
    window.localStorage.setItem(
      "application-form-local-draft",
      JSON.stringify([
        { seminarId: "sem-2", reason: "試し書き" },
        { seminarId: "", reason: "" },
        { seminarId: "", reason: "" },
      ]),
    );

    const submitted = emptyDraft({
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
      <ApplicationForm seminars={seminars} initialApplication={submitted} />,
    );

    expect(screen.getByDisplayValue("興味があるため")).toBeInTheDocument();
    expect(screen.queryByDisplayValue("試し書き")).not.toBeInTheDocument();
  });
});
