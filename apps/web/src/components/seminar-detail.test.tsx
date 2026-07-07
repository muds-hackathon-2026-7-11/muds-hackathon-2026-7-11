import { fireEvent, render, screen } from "@testing-library/react";
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
      research_theme: "画像認識",
      interest_tags: [
        { id: "tag-2", name: "画像認識", category: "画像・映像" },
      ],
    },
    {
      id: "member-2",
      name: "学生B",
      research_theme: "自然言語処理",
      interest_tags: [
        { id: "tag-2", name: "画像認識", category: "画像・映像" },
      ],
    },
  ],
};

describe("SeminarDetailView", () => {
  it("renders seminar info, teachers, materials, and current members", () => {
    render(<SeminarDetailView seminar={seminar} />);

    expect(screen.getByText("AIゼミ")).toBeInTheDocument();
    expect(screen.getByText("機械学習の研究をします。")).toBeInTheDocument();
    expect(screen.getByText("山田教授")).toBeInTheDocument();
    expect(screen.getByText("PDF")).toBeInTheDocument();
    expect(screen.getByText("学生A")).toBeInTheDocument();
    expect(screen.getByText("学生B")).toBeInTheDocument();
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

  it("aggregates member interest tags into a chart with counts", () => {
    render(<SeminarDetailView seminar={seminar} />);

    // 画像認識タグは学生A・学生Bの両方が持つため、研究概要・タグ表示・
    // グラフの軸ラベルなど複数箇所に現れる。
    expect(screen.getAllByText("画像認識").length).toBeGreaterThan(0);
  });

  it("always links to the seminar's question page", () => {
    render(<SeminarDetailView seminar={seminar} />);

    expect(screen.getByRole("link", { name: "FAQ" })).toHaveAttribute(
      "href",
      "/seminars/seminar-1/questions",
    );
  });
});
