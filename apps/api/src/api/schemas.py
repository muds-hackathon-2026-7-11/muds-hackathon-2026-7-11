import uuid
from datetime import date, datetime
from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator

from api.models import (
    ApplicationStatus,
    MaterialType,
    QuestionStatus,
    RecruitmentTermStatus,
    UserRole,
)


class ResearchTagOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    category: str


class CurrentSeminarOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str


class MeOut(BaseModel):
    """認証済みユーザー自身の情報(GET /me)。"""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    name: str
    role: UserRole
    student_id: str | None
    grade: str | None
    research_title: str | None
    research_theme: str | None
    interest_tags: list[ResearchTagOut]
    slack_user_id: str | None
    # 現在の年度に所属しているゼミ(学生のみ。無ければNone)。
    current_seminar: CurrentSeminarOut | None


class MeUpdateIn(BaseModel):
    """本人の研究タイトル・研究概要・興味分野タグの更新(PATCH /me)。"""

    research_title: str | None = Field(default=None, max_length=200)
    research_theme: str | None = Field(default=None, max_length=2000)
    interest_tag_ids: list[uuid.UUID] = Field(default_factory=list, max_length=20)


class UserExistsOut(BaseModel):
    """メールアドレスが事前登録済みか(ログイン許可判定用)。"""

    exists: bool


class SeminarOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None
    photo_url: str | None
    capacity: int | None
    recruitment_start: date | None
    recruitment_end: date | None


class TeacherOut(BaseModel):
    id: uuid.UUID
    name: str
    photo_url: str | None
    research_title: str | None
    research_theme: str | None
    interest_tags: list[ResearchTagOut]


class SeminarMaterialOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    url: str
    type: MaterialType


class SeminarMemberOut(BaseModel):
    id: uuid.UUID
    name: str
    grade: str | None
    research_title: str | None
    research_theme: str | None
    interest_tags: list[ResearchTagOut]


class SeminarDetailOut(SeminarOut):
    teachers: list[TeacherOut]
    materials: list[SeminarMaterialOut]
    current_members: list[SeminarMemberOut]


class PriorityCounts(BaseModel):
    """第1〜第3志望それぞれの人数。"""

    first: int
    second: int
    third: int


class SeminarStatsOut(BaseModel):
    """ゼミごとの応募状況（現在の募集ラウンド基準）。"""

    id: uuid.UUID
    name: str
    capacity: int | None
    applicant_count: int
    priority_counts: PriorityCounts
    # 学年(users.grade)別の志望人数(累計)。grade未設定は "不明"。
    grade_counts: dict[str, int]
    # 志望順位(1〜3)ごとの学年別人数。キーは "1"/"2"/"3"、内側は学年→人数。
    # 例: {"1": {"B3": 2, "B4": 1}, "2": {"B3": 1}, "3": {}}
    # 応募状況グラフで「各志望順位の人数を学年で積み上げる」ために使う。
    priority_grade_counts: dict[str, dict[str, int]]
    # 倍率 = applicant_count / capacity。定員が未設定/0 の場合は null。
    ratio: float | None
    # 現在の所属ゼミ生数（継続者）。
    continuing_count: int
    # 継続希望人数: 現在の所属ゼミ生のうち、今回の募集ラウンドで
    # 同じゼミを第1志望に選んだ人数。
    continuing_first_choice_count: int
    # 対象学年(#99)。未設定(募集ラウンドの設定行が無い)ならnull。
    target_grades: list[str] | None
    # アイコン表示用(#139)。ゼミ自体の写真。
    photo_url: str | None
    # アイコン表示用(#139)。担当教員が1人だけの場合に限りその教員の写真を
    # 使う(複数教員のゼミは特定の1人を代表にできないためnull)。
    teacher_photo_url: str | None


class QuestionCreate(BaseModel):
    seminar_id: uuid.UUID
    slack_user_id: str
    content: str = Field(min_length=1, max_length=2000)


class QuestionCreateWeb(BaseModel):
    """Web(FAQ画面)からの質問投稿(#141)。

    Slack Bot経由のQuestionCreateとは別経路。投稿者はslack_user_idではなく
    Web認証済みユーザーで特定する。投稿時のSlack通知はQuestionCreateと同じ
    notify_answer_candidatesを使う(#143)。
    """

    seminar_id: uuid.UUID
    content: str = Field(min_length=1, max_length=2000)


class QuestionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    seminar_id: uuid.UUID
    content: str
    status: QuestionStatus
    created_at: datetime


class AnswerOut(BaseModel):
    id: uuid.UUID
    content: str
    answerer_name: str
    created_at: datetime


class QuestionWithAnswersOut(QuestionOut):
    answers: list[AnswerOut]


class AnswerCreate(BaseModel):
    question_id: uuid.UUID
    slack_user_id: str
    content: str = Field(min_length=1, max_length=2000)


class ApplicationChoiceIn(BaseModel):
    seminar_id: uuid.UUID
    priority: int = Field(ge=1, le=3)
    reason: str = Field(max_length=400)


class ApplicationUpsertIn(BaseModel):
    choices: list[ApplicationChoiceIn] = Field(max_length=3)


class ApplicationChoiceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    seminar_id: uuid.UUID
    priority: int
    reason: str
    match_score: int | None
    match_feedback: dict | None


class ApplicationFormOut(BaseModel):
    id: uuid.UUID | None
    status: ApplicationStatus
    submitted_at: datetime | None
    choices: list[ApplicationChoiceOut]
    # 現在アクティブな募集期間の内容ならtrue。falseは過去期間の閲覧専用表示
    # (提出期間外でも直近の提出内容は見えるが、編集・再提出はできない)。
    is_editable: bool


# --- 運営: 募集ラウンド・定員設定 (#57) ---


class RecruitmentTermCreate(BaseModel):
    academic_year: int
    starts_at: date
    ends_at: date
    status: RecruitmentTermStatus = RecruitmentTermStatus.preparing


class RecruitmentTermUpdate(BaseModel):
    starts_at: date | None = None
    ends_at: date | None = None
    status: RecruitmentTermStatus | None = None


class RecruitmentTermOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    academic_year: int
    starts_at: date
    ends_at: date
    status: RecruitmentTermStatus


class SeminarRecruitmentUpsert(BaseModel):
    capacity: int = Field(ge=0)
    # 募集対象学年(#99)。空リストは「募集していない」を意味する。
    # このエンドポイントは全置換なので必須にする(省略時に暗黙で
    # 閉じる/開くのどちらかにフォールバックすると、teacher.py側の
    # 「省略時は既存値据え置き」という別の省略時挙動と食い違うため)。
    target_grades: list[Literal["B1", "B2", "B3", "B4"]]


class SeminarRecruitmentOut(BaseModel):
    """募集ラウンドでのゼミ別設定。未設定のゼミは値が null。"""

    seminar_id: uuid.UUID
    seminar_name: str
    capacity: int | None
    target_grades: list[str] | None


# --- 教員向け応募者管理 (#58) ---


class PastSeminarOut(BaseModel):
    seminar_name: str
    academic_year: int


class ApplicantOut(BaseModel):
    student_id: str | None
    name: str
    grade: str | None
    priority: int
    reason: str
    research_title: str | None
    research_theme: str | None
    past_seminars: list[PastSeminarOut]


class SeminarApplicantsOut(BaseModel):
    seminar_id: uuid.UUID
    seminar_name: str
    applicants: list[ApplicantOut]


class UnsubmittedApplicantOut(BaseModel):
    student_id: str | None
    name: str
    grade: str | None
    # 表示用の生のgradeとは別に、学年フィルタ用のB1〜B4正規化済み値を返す。
    # normalize_gradeの正規化ルールをフロントで再実装すると二重管理になり
    # 食い違う(#182)ため、判定はAPI側の1箇所に寄せる。
    normalized_grade: str | None


class TeacherRecruitmentUpdate(BaseModel):
    capacity: int = Field(ge=0)
    # Noneなら据え置き(現状の対象学年を変更しない)。
    target_grades: list[Literal["B1", "B2", "B3", "B4"]] | None = None


class TeacherRecruitmentOut(BaseModel):
    seminar_id: uuid.UUID
    seminar_name: str
    capacity: int | None
    target_grades: list[str] | None


class TeacherSeminarUpdate(BaseModel):
    """教員が自分の担当ゼミの紹介内容を編集する(#149)。名称変更・削除・担当の
    付け外しはadmin専用のまま(AdminSeminarUpdateとは別スキーマ)。"""

    description: str | None = None
    photo_url: str | None = None


# --- マッチ度診断 (#59) ---


class MatchOut(BaseModel):
    seminar_id: uuid.UUID
    score: int | None
    feedback: dict | None
    # score を出せない場合(研究テーマ/ゼミ紹介が未設定など)の説明。
    message: str | None = None


# --- 一括マッチ度診断 (#118) ---


class SeminarMatchOut(BaseModel):
    seminar_id: uuid.UUID
    seminar_name: str
    score: int  # ルーブリック観点の加重総合(0-100)
    # 観点別スコア {"field","method","interest","style"}(各0-100)。
    rubric: dict
    summary: str
    reasons: list[str]


class SeminarMatchesOut(BaseModel):
    # score 降順。算出不可の場合は空リスト + message。
    results: list[SeminarMatchOut]
    message: str | None = None


# --- 志望理由ごとのマッチ度診断 (#119) ---


class ReasonMatchIn(BaseModel):
    seminar_id: uuid.UUID
    reason: str = Field(max_length=400)


class ReasonMatchesIn(BaseModel):
    choices: list[ReasonMatchIn] = Field(max_length=3)


class ReasonMatchRecommendation(BaseModel):
    seminar_id: uuid.UUID
    seminar_name: str
    score: int  # 0-100


class ReasonMatchResult(BaseModel):
    seminar_id: uuid.UUID  # 志望に選んだゼミ
    seminar_name: str
    # 選んだゼミ自身のマッチ度(採点対象外=紹介文/資料が無い等ならnull)。
    selected_score: int | None
    rubric: dict
    summary: str
    # この志望理由に相性の良い他ゼミTop3(第1〜3志望のゼミは除外)。
    recommendations: list[ReasonMatchRecommendation]


class ReasonMatchesOut(BaseModel):
    # choices と同じ並び。志望理由が空のスロットは含まない。
    results: list[ReasonMatchResult]
    message: str | None = None


# --- 運営: 教員・ゼミ管理 (#62) ---
# 新規の一括投入はCSV(#40/#45)が担うため、ここは個別の編集・担当の付け外しが中心。


class AdminSeminarCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    photo_url: str | None = None


class AdminSeminarUpdate(BaseModel):
    # 送られたフィールドのみ更新する(未指定は据え置き)。ルーター側で
    # model_dump(exclude_unset=True) を使うため、既定値は「未指定」を表す。
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    photo_url: str | None = None


class AdminSeminarTeacherOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str


class SeminarMaterialCreate(BaseModel):
    url: str = Field(min_length=1)
    type: MaterialType

    @field_validator("url")
    @classmethod
    def _require_http_scheme(cls, value: str) -> str:
        # javascript: 等のスキームだと、フロント側でこのURLをそのまま
        # <a href> に使った際にクリックで実行されてしまう(#172)。
        # 資料リンクはhttp(s)のみを許可する。
        scheme = urlsplit(value).scheme.lower()
        if scheme not in ("http", "https"):
            raise ValueError("資料URLはhttp(s)から始まるURLを入力してください。")
        return value


class AdminSeminarOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None
    photo_url: str | None
    teachers: list[AdminSeminarTeacherOut]
    materials: list[SeminarMaterialOut]


class AdminTeacherCreate(BaseModel):
    # 教員ユーザーを1名追加する(作成はここ、一括はCSV #40)。
    name: str = Field(min_length=1, max_length=200)
    email: str = Field(min_length=3, max_length=255)
    research_title: str | None = None
    research_theme: str | None = None
    photo_url: str | None = None

    @field_validator("email")
    @classmethod
    def _normalize_email(cls, value: str) -> str:
        # import系と揃えて小文字正規化し、最低限の形式チェックを行う。
        normalized = value.strip().lower()
        if "@" not in normalized:
            raise ValueError("有効なメールアドレスを入力してください。")
        return normalized


class AdminTeacherUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    email: str | None = Field(default=None, min_length=3, max_length=255)
    research_title: str | None = None
    research_theme: str | None = None
    photo_url: str | None = None
    is_active: bool | None = None

    @field_validator("email")
    @classmethod
    def _normalize_email(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower()
        if "@" not in normalized:
            raise ValueError("有効なメールアドレスを入力してください。")
        return normalized


class AdminTeacherOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    email: str
    research_title: str | None
    research_theme: str | None
    photo_url: str | None
    is_active: bool


# --- 管理者管理(#134) ---
# 管理者は教員とは完全に独立したユーザー(role=admin)として扱う。
# 新規作成はせず、既にusers(学生・教員)に登録済みのメールアドレスから
# 既存ユーザーを探してroleをadminに変更する形で追加する。


class AdminUserCreate(BaseModel):
    email: str = Field(min_length=3, max_length=255)

    @field_validator("email")
    @classmethod
    def _normalize_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if "@" not in normalized:
            raise ValueError("有効なメールアドレスを入力してください。")
        return normalized


class AdminUserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    email: str
    is_active: bool


class AdminUserLookupOut(BaseModel):
    """管理者追加前に、メールアドレスから既存ユーザーの名前を確認するための表示用。"""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    email: str
    role: UserRole
    is_active: bool


# --- 配属結果CSVインポート (#61) ---


class AssignmentImportError(BaseModel):
    # CSVの行番号(ヘッダを除いた1始まり)と理由。
    row: int
    reason: str


class AssignmentImportResult(BaseModel):
    created: int  # 新規に作成した配属レコード数
    existing: int  # 既に存在していた(スキップした)数
    errors: list[AssignmentImportError]


# --- 学生・教員名簿CSVインポート (#163) ---


class UserImportSkip(BaseModel):
    # CSVの行番号(ヘッダを除いた1始まり)・メールアドレス・スキップ理由。
    row: int
    email: str
    reason: str


class UserImportResult(BaseModel):
    created: int  # 新規に作成したユーザー数
    updated: int  # 既存ユーザーで更新した数(学年変更等)
    deactivated: int  # CSVに存在しなくなり非アクティブ化した学生数
    skipped: list[UserImportSkip]


# --- AIゼミ相談アシスタント (requirements §2 / chat_logs) ---


class ConsultTurnIn(BaseModel):
    # 会話履歴の1発話。role は "user" / "assistant"。
    role: str = Field(pattern="^(user|assistant)$")
    content: str = Field(min_length=1, max_length=4000)


class ConsultIn(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    # 継続会話用。直近の履歴(なければ空)。長すぎる分はサーバ側で切り詰める。
    history: list[ConsultTurnIn] = Field(default_factory=list, max_length=20)


class ConsultRecommendation(BaseModel):
    seminar_name: str
    reason: str


class ConsultOut(BaseModel):
    reply: str
    recommendations: list[ConsultRecommendation]
