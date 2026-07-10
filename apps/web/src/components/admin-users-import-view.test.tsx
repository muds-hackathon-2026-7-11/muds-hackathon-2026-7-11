import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useSession } from "next-auth/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AdminUsersImportView } from "./admin-users-import-view";

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
    [
      "username,email,status,billing-active,has-2fa,has-sso,userid,fullname,displayname,expiration-timestamp\n",
    ],
    "slack_member.csv",
    { type: "text/csv" },
  );
}

function getFileInput(): HTMLInputElement {
  return document.querySelector('input[type="file"]') as HTMLInputElement;
}

describe("AdminUsersImportView", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("shows an error when uploading with no file selected", async () => {
    const user = userEvent.setup();
    const fetchSpy = vi.spyOn(globalThis, "fetch");

    render(<AdminUsersImportView />);
    await user.click(screen.getByRole("button", { name: "アップロードする" }));

    expect(
      await screen.findByText("CSVファイルを選択してください。"),
    ).toBeInTheDocument();
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("selects a file dropped onto the drop zone", async () => {
    render(<AdminUsersImportView />);

    const dropZone = screen.getByRole("button", {
      name: /ドラッグ&ドロップ/,
    });
    fireEvent.drop(dropZone, {
      dataTransfer: { files: [makeCsvFile()] },
    });

    expect(await screen.findByText("slack_member.csv")).toBeInTheDocument();
  });

  it("shows an error when the dropped file is not a .csv", async () => {
    render(<AdminUsersImportView />);

    const dropZone = screen.getByRole("button", {
      name: /ドラッグ&ドロップ/,
    });
    const notCsv = new File(["hello"], "notes.txt", { type: "text/plain" });
    fireEvent.drop(dropZone, { dataTransfer: { files: [notCsv] } });

    expect(
      await screen.findByText("CSVファイル(.csv)を選択してください。"),
    ).toBeInTheDocument();
    expect(screen.getByText("未選択")).toBeInTheDocument();
  });

  it("uploads the selected CSV as multipart form data on button click", async () => {
    const user = userEvent.setup();
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({ created: 2, updated: 1, deactivated: 0, skipped: [] }),
        { status: 200 },
      ),
    );

    render(<AdminUsersImportView />);
    await user.upload(getFileInput(), makeCsvFile());
    expect(screen.getByText("slack_member.csv")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "アップロードする" }));

    await waitFor(() => {
      expect(fetchSpy).toHaveBeenCalledWith(
        expect.stringContaining("/admin/users/import"),
        expect.objectContaining({ method: "POST" }),
      );
    });
    const [, init] = fetchSpy.mock.calls[0];
    expect(init?.body).toBeInstanceOf(FormData);
    const formData = init?.body as FormData;
    expect((formData.get("file") as File).name).toBe("slack_member.csv");

    expect(await screen.findByText("2")).toBeInTheDocument();
    expect(screen.getByText("1")).toBeInTheDocument();
  });

  it("clears the file input after a successful upload", async () => {
    const user = userEvent.setup();
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({ created: 1, updated: 0, deactivated: 0, skipped: [] }),
        { status: 200 },
      ),
    );

    render(<AdminUsersImportView />);
    const fileInput = getFileInput();
    await user.upload(fileInput, makeCsvFile());
    await user.click(screen.getByRole("button", { name: "アップロードする" }));

    await screen.findByText("1");
    expect(fileInput.value).toBe("");
    expect(screen.getByText("未選択")).toBeInTheDocument();
  });

  it("shows skipped rows from the result", async () => {
    const user = userEvent.setup();
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          created: 1,
          updated: 0,
          deactivated: 0,
          skipped: [
            {
              row: 2,
              email: "someone@example.com",
              reason: "氏名欄をパースできません",
            },
          ],
        }),
        { status: 200 },
      ),
    );

    render(<AdminUsersImportView />);
    await user.upload(getFileInput(), makeCsvFile());
    await user.click(screen.getByRole("button", { name: "アップロードする" }));

    expect(
      await screen.findByText(
        "2行目(someone@example.com): 氏名欄をパースできません",
      ),
    ).toBeInTheDocument();
  });

  it("shows an error message when the upload fails", async () => {
    const user = userEvent.setup();
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ detail: "権限がありません。" }), {
        status: 403,
      }),
    );

    render(<AdminUsersImportView />);
    await user.upload(getFileInput(), makeCsvFile());
    await user.click(screen.getByRole("button", { name: "アップロードする" }));

    expect(await screen.findByText("権限がありません。")).toBeInTheDocument();
  });
});
