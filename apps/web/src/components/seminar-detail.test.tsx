import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { SeminarDetailView, type SeminarDetail } from "./seminar-detail";

const seminar: SeminarDetail = {
  id: "seminar-1",
  name: "AIゼミ",
  description: "機械学習の研究をします。",
  photo_url: null,
  capacity: 10,
  teachers: [
    {
      id: "teacher-1",
      name: "山田教授",
      photo_url: null,
      research_title: "深層学習モデルの研究",
      research_theme: "深層学習",
      interest_tags: [
        { id: "tag-1", name: "深層学習", category: "AI・機械学習" },
      ],
    },
  ],
  materials: [
    { id: "material-1", url: "https://example.com/a.pdf", type: "pdf" },
  ],
  current_members: [
    {
      id: "member-1",
      name: "学生A",
      grade: "B3",
      research_title: "画像認識の精度向上",
      research_theme: "画像認識",
      interest_tags: [
        { id: "tag-2", name: "画像認識", category: "画像・映像" },
      ],
    },
    {
      id: "member-2",
      name: "学生B",
      grade: "B4",
      research_title: null,
      research_theme: "自然言語処理",
      interest_tags: [
        { id: "tag-2", name: "画像認識", category: "画像・映像" },
      ],
    },
  ],
};

describe("SeminarDetailView", () => {
  it("links back to the 応募状況 page", () => {
    render(<SeminarDetailView seminar={seminar} />);

    expect(
      screen.getByRole("link", { name: "← 応募状況に戻る" }),
    ).toHaveAttribute("href", "/assignment");
  });

  it("renders seminar info, teachers, materials, and current members", () => {
    render(<SeminarDetailView seminar={seminar} />);

    expect(screen.getByText("AIゼミ")).toBeInTheDocument();
    expect(screen.getByText("機械学習の研究をします。")).toBeInTheDocument();
    expect(screen.getByText("山田教授")).toBeInTheDocument();
    expect(screen.getByText("深層学習モデルの研究")).toBeInTheDocument();
    expect(screen.getByText("PDF")).toBeInTheDocument();
    // 学年を名前の前に付けて表示し、その下に研究タイトルを出す。
    expect(screen.getByText("B3 学生A")).toBeInTheDocument();
    expect(screen.getByText("画像認識の精度向上")).toBeInTheDocument();
    expect(screen.getByText("B4 学生B")).toBeInTheDocument();
  });

  it("falls back to a placeholder when a member's research title is unset", () => {
    render(<SeminarDetailView seminar={seminar} />);

    expect(screen.getByText("研究タイトル未設定")).toBeInTheDocument();
  });

  it("shows the teacher's initial when neither teacher nor seminar photo is set", () => {
    render(<SeminarDetailView seminar={seminar} />);

    expect(screen.getByText("山")).toBeInTheDocument();
    expect(screen.queryByAltText("山田教授")).not.toBeInTheDocument();
  });

  it("falls back to the initial when the photo fails to load", () => {
    const withPhoto: SeminarDetail = {
      ...seminar,
      teachers: [
        {
          ...seminar.teachers[0],
          photo_url: "https://example.com/broken.jpg",
        },
      ],
    };
    render(<SeminarDetailView seminar={withPhoto} />);

    fireEvent.error(screen.getByAltText("山田教授"));

    expect(screen.getByText("山")).toBeInTheDocument();
    expect(screen.queryByAltText("山田教授")).not.toBeInTheDocument();
  });

  it("shows the teacher's own photo when set and the seminar has no photo", () => {
    const withPhoto: SeminarDetail = {
      ...seminar,
      teachers: [
        {
          ...seminar.teachers[0],
          photo_url: "https://example.com/teacher.jpg",
        },
      ],
    };
    render(<SeminarDetailView seminar={withPhoto} />);

    expect(screen.getByAltText("山田教授")).toHaveAttribute(
      "src",
      "https://example.com/teacher.jpg",
    );
  });

  it("prefers the seminar's own photo over the teacher's photo", () => {
    const withBothPhotos: SeminarDetail = {
      ...seminar,
      photo_url: "https://example.com/seminar.jpg",
      teachers: [
        {
          ...seminar.teachers[0],
          photo_url: "https://example.com/teacher.jpg",
        },
      ],
    };
    render(<SeminarDetailView seminar={withBothPhotos} />);

    expect(screen.getByAltText("山田教授")).toHaveAttribute(
      "src",
      "https://example.com/seminar.jpg",
    );
  });

  it("opens a dialog with the member's research theme and tags when clicked", () => {
    render(<SeminarDetailView seminar={seminar} />);

    // 初期状態ではモーダル(dialog)は開いていない。
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();

    // 名前をクリックすると画面中央にモーダルが開き、研究概要とタグが現れる。
    fireEvent.click(screen.getByRole("button", { name: /学生A/ }));

    const dialog = screen.getByRole("dialog");
    expect(dialog).toBeInTheDocument();
    expect(within(dialog).getAllByText("画像認識").length).toBeGreaterThan(0);
  });

  it("always links to the seminar's question page", () => {
    render(<SeminarDetailView seminar={seminar} />);

    expect(screen.getByRole("link", { name: "FAQ" })).toHaveAttribute(
      "href",
      "/seminars/seminar-1/questions",
    );
  });
});
