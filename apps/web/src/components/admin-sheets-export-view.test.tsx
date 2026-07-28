import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useSession } from "next-auth/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AdminSheetsExportView } from "./admin-sheets-export-view";

vi.mock("next-auth/react", () => ({
  useSession: vi.fn(),
}));

vi.mocked(useSession).mockReturnValue({
  data: null,
  status: "unauthenticated",
  update: vi.fn(),
});

describe("AdminSheetsExportView", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("shows a not-issued message and an issue button when there is no key yet", () => {
    render(<AdminSheetsExportView initialKey={null} />);

    expect(screen.getByText("まだ発行されていません。")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "発行する" }),
    ).toBeInTheDocument();
  });

  it("shows the existing key and a regenerate button when already issued", () => {
    render(<AdminSheetsExportView initialKey="existing-key" />);

    expect(screen.getByText("existing-key")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "再発行する" }),
    ).toBeInTheDocument();
  });

  it("issues a new key without confirmation when none exists yet", async () => {
    const user = userEvent.setup();
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify({ key: "brand-new-key" }), { status: 200 }),
    );

    render(<AdminSheetsExportView initialKey={null} />);
    await user.click(screen.getByRole("button", { name: "発行する" }));

    expect(await screen.findByText("brand-new-key")).toBeInTheDocument();
  });

  it("asks for confirmation before regenerating an existing key", async () => {
    const user = userEvent.setup();
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(false);
    const fetchSpy = vi.spyOn(globalThis, "fetch");

    render(<AdminSheetsExportView initialKey="existing-key" />);
    await user.click(screen.getByRole("button", { name: "再発行する" }));

    expect(confirmSpy).toHaveBeenCalled();
    expect(fetchSpy).not.toHaveBeenCalled();
    expect(screen.getByText("existing-key")).toBeInTheDocument();
  });

  it("copies the key to the clipboard", async () => {
    const user = userEvent.setup();
    // userEvent.setup()が独自のclipboardスタブを入れるため、この後で上書きする。
    const writeTextMock = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", {
      value: { writeText: writeTextMock },
      configurable: true,
    });
    render(<AdminSheetsExportView initialKey="existing-key" />);

    await user.click(screen.getByRole("button", { name: "コピー" }));

    expect(writeTextMock).toHaveBeenCalledWith("existing-key");
    expect(
      screen.getByRole("button", { name: "コピーしました" }),
    ).toBeInTheDocument();
  });
});
