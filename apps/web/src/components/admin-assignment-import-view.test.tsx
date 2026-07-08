import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useSession } from "next-auth/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AdminAssignmentImportView } from "./admin-assignment-import-view";

vi.mock("next-auth/react", () => ({
  useSession: vi.fn(),
}));

vi.mocked(useSession).mockReturnValue({
  data: null,
  status: "unauthenticated",
  update: vi.fn(),
});

function makeCsvFile(): File {
  return new File(
    ["student_id,seminar_id,term_id\ns2311001,seminar-1,term-1\n"],
    "assignments.csv",
    { type: "text/csv" },
  );
}

function getFileInput(): HTMLInputElement {
  return document.querySelector('input[type="file"]') as HTMLInputElement;
}

describe("AdminAssignmentImportView", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("shows a single button that opens the file picker", () => {
    render(<AdminAssignmentImportView />);

    expect(
      screen.getByRole("button", { name: "CSVファイルを選択してアップロード" }),
    ).toBeInTheDocument();
  });

  it("uploads the CSV as multipart form data as soon as it is selected", async () => {
    const user = userEvent.setup();
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ created: 2, existing: 1, errors: [] }), {
        status: 200,
      }),
    );

    render(<AdminAssignmentImportView />);
    await user.upload(getFileInput(), makeCsvFile());

    await waitFor(() => {
      expect(fetchSpy).toHaveBeenCalledWith(
        expect.stringContaining("/admin/assignments/import"),
        expect.objectContaining({ method: "POST" }),
      );
    });
    const [, init] = fetchSpy.mock.calls[0];
    expect(init?.body).toBeInstanceOf(FormData);
    expect(
      (init?.headers as Headers | undefined)?.get?.("Content-Type"),
    ).not.toBe("application/json");

    expect(await screen.findByText("2")).toBeInTheDocument();
    expect(screen.getByText("1")).toBeInTheDocument();
  });

  it("clears the file input after a successful upload", async () => {
    const user = userEvent.setup();
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ created: 1, existing: 0, errors: [] }), {
        status: 200,
      }),
    );

    render(<AdminAssignmentImportView />);
    const fileInput = getFileInput();
    await user.upload(fileInput, makeCsvFile());

    await screen.findByText("1");
    expect(fileInput.value).toBe("");
  });

  it("shows row-level errors from the result", async () => {
    const user = userEvent.setup();
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

    render(<AdminAssignmentImportView />);
    await user.upload(getFileInput(), makeCsvFile());

    expect(
      await screen.findByText("2行目: 学生が見つかりません: s9999999"),
    ).toBeInTheDocument();
  });

  it("shows an error message when the upload fails", async () => {
    const user = userEvent.setup();
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ detail: "権限がありません。" }), {
        status: 403,
      }),
    );

    render(<AdminAssignmentImportView />);
    await user.upload(getFileInput(), makeCsvFile());

    expect(await screen.findByText("権限がありません。")).toBeInTheDocument();
  });
});
