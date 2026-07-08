import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useSession } from "next-auth/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import {
  AdminAssignmentImportView,
  type AdminTermOption,
} from "./admin-assignment-import-view";

vi.mock("next-auth/react", () => ({
  useSession: vi.fn(),
}));

vi.mocked(useSession).mockReturnValue({
  data: null,
  status: "unauthenticated",
  update: vi.fn(),
});

function makeTerm(overrides: Partial<AdminTermOption> = {}): AdminTermOption {
  return {
    id: "term-1",
    academic_year: 2027,
    starts_at: "2026-07-07",
    ends_at: "2027-04-03",
    ...overrides,
  };
}

function makeCsvFile(): File {
  return new File(
    ["student_id,seminar_id\ns2311001,seminar-1\n"],
    "assignments.csv",
    { type: "text/csv" },
  );
}

function getFileInput(): HTMLInputElement {
  return document.querySelector('input[type="file"]') as HTMLInputElement;
}

async function selectTerm(
  user: ReturnType<typeof userEvent.setup>,
  term: AdminTermOption,
) {
  await user.selectOptions(screen.getByLabelText("募集ラウンド"), term.id);
}

describe("AdminAssignmentImportView", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("shows a message and a link to create one when there are no terms", () => {
    render(<AdminAssignmentImportView terms={[]} />);

    expect(
      screen.getByText(/募集ラウンドがまだありません/),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "募集ラウンド管理" }),
    ).toHaveAttribute("href", "/admin/recruitment-terms");
  });

  it("links to the seminar management screen to look up seminar_id", () => {
    render(<AdminAssignmentImportView terms={[makeTerm()]} />);

    expect(screen.getByRole("link", { name: "ゼミ管理" })).toHaveAttribute(
      "href",
      "/admin/seminars",
    );
  });

  it("does not upload until both a term and a file are chosen", async () => {
    const user = userEvent.setup();
    const fetchSpy = vi.spyOn(globalThis, "fetch");
    const term = makeTerm();

    render(<AdminAssignmentImportView terms={[term]} />);
    await user.click(screen.getByRole("button", { name: "アップロードする" }));

    expect(
      await screen.findByText("募集ラウンドを選択してください。"),
    ).toBeInTheDocument();
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("shows an error when a term is chosen but no file is selected", async () => {
    const user = userEvent.setup();
    const fetchSpy = vi.spyOn(globalThis, "fetch");
    const term = makeTerm();

    render(<AdminAssignmentImportView terms={[term]} />);
    await selectTerm(user, term);
    await user.click(screen.getByRole("button", { name: "アップロードする" }));

    expect(
      await screen.findByText("CSVファイルを選択してください。"),
    ).toBeInTheDocument();
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("uploads the selected term_id and CSV as multipart form data on button click", async () => {
    const user = userEvent.setup();
    const term = makeTerm();
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ created: 2, existing: 1, errors: [] }), {
        status: 200,
      }),
    );

    render(<AdminAssignmentImportView terms={[term]} />);
    await selectTerm(user, term);
    await user.upload(getFileInput(), makeCsvFile());
    expect(screen.getByText("assignments.csv")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "アップロードする" }));

    await waitFor(() => {
      expect(fetchSpy).toHaveBeenCalledWith(
        expect.stringContaining("/admin/assignments/import"),
        expect.objectContaining({ method: "POST" }),
      );
    });
    const [, init] = fetchSpy.mock.calls[0];
    expect(init?.body).toBeInstanceOf(FormData);
    const formData = init?.body as FormData;
    expect(formData.get("term_id")).toBe(term.id);
    expect((formData.get("file") as File).name).toBe("assignments.csv");

    expect(await screen.findByText("2")).toBeInTheDocument();
    expect(screen.getByText("1")).toBeInTheDocument();
  });

  it("clears the file input after a successful upload", async () => {
    const user = userEvent.setup();
    const term = makeTerm();
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ created: 1, existing: 0, errors: [] }), {
        status: 200,
      }),
    );

    render(<AdminAssignmentImportView terms={[term]} />);
    await selectTerm(user, term);
    const fileInput = getFileInput();
    await user.upload(fileInput, makeCsvFile());
    await user.click(screen.getByRole("button", { name: "アップロードする" }));

    await screen.findByText("1");
    expect(fileInput.value).toBe("");
    expect(screen.getByText("未選択")).toBeInTheDocument();
  });

  it("shows row-level errors from the result", async () => {
    const user = userEvent.setup();
    const term = makeTerm();
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          created: 1,
          existing: 0,
          errors: [{ row: 2, reason: "学生が見つかりません: s9999999" }],
        }),
        { status: 200 },
      ),
    );

    render(<AdminAssignmentImportView terms={[term]} />);
    await selectTerm(user, term);
    await user.upload(getFileInput(), makeCsvFile());
    await user.click(screen.getByRole("button", { name: "アップロードする" }));

    expect(
      await screen.findByText("2行目: 学生が見つかりません: s9999999"),
    ).toBeInTheDocument();
  });

  it("shows an error message when the upload fails", async () => {
    const user = userEvent.setup();
    const term = makeTerm();
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ detail: "権限がありません。" }), {
        status: 403,
      }),
    );

    render(<AdminAssignmentImportView terms={[term]} />);
    await selectTerm(user, term);
    await user.upload(getFileInput(), makeCsvFile());
    await user.click(screen.getByRole("button", { name: "アップロードする" }));

    expect(await screen.findByText("権限がありません。")).toBeInTheDocument();
  });
});
