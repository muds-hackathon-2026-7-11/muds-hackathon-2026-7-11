import pytest
from sqlalchemy import select

from api.import_users import (
    _deactivate_missing_users,
    _get_or_create_user,
    _is_deactivated_in_slack,
    import_rows,
    parse_fullname,
)
from api.models import User, UserRole


def test_parses_plain_grade() -> None:
    profile = parse_fullname(
        "[B1] 山田 太郎 / Taro Yamada", "s2622014@stu.musashino-u.ac.jp"
    )
    assert profile is not None
    assert profile.name == "山田 太郎"
    assert profile.role == UserRole.student
    assert profile.grade == "B1"
    assert profile.student_id == "s2622014"


def test_normalizes_whitespace_around_slash_in_grade() -> None:
    profile = parse_fullname(
        "[MIDS / B4] 鈴木 亮次 / Ryoji Suzuki", "s2394007@stu.musashino-u.ac.jp"
    )
    assert profile is not None
    assert profile.grade == "MIDS/B4"


def test_keeps_guest_qualifier_as_is() -> None:
    profile = parse_fullname(
        "[M2 guest] 陳 昊宇 / Kouu Chin", "g2550008@stu.musashino-u.ac.jp"
    )
    assert profile is not None
    assert profile.grade == "M2 guest"


def test_graduate_student_id_uses_g_prefix() -> None:
    profile = parse_fullname(
        "[M1] 甘 楚渢 / Ama Sohuu", "g2650002@stu.musashino-u.ac.jp"
    )
    assert profile is not None
    assert profile.student_id == "g2650002"


def test_teacher_bracket_has_no_grade_or_student_id() -> None:
    profile = parse_fullname(
        "[教員] ソンラートラムワニッチ ウィラット / Virach Sornlertlamvanich",
        "virach@gmail.com",
    )
    assert profile is not None
    assert profile.name == "ソンラートラムワニッチ ウィラット"
    assert profile.role == UserRole.teacher
    assert profile.grade is None
    assert profile.student_id is None


def test_non_student_id_shaped_email_leaves_student_id_none() -> None:
    # ゲスト学生がgmail等の私用メールで参加しているケース。
    profile = parse_fullname("[M1 guest] 単 詩軒 / Shiken Zen", "qwq77521w@gmail.com")
    assert profile is not None
    assert profile.role == UserRole.student
    assert profile.student_id is None


def test_returns_none_when_fullname_has_no_bracket() -> None:
    profile = parse_fullname("山田 太郎", "s0000000-test@stu.musashino-u.ac.jp")
    assert profile is None


def test_is_deactivated_in_slack_true_for_deactivated_status() -> None:
    assert _is_deactivated_in_slack({"status": "Deactivated"}) is True


@pytest.mark.parametrize("status", ["Member", "Admin", "Owner", "Primary Owner", ""])
def test_is_deactivated_in_slack_false_for_non_deactivated_status(status: str) -> None:
    # billing-active=0でもMemberとして現役のケースが実際にあったため、
    # statusだけで判定し、billing-activeは見ない。
    assert _is_deactivated_in_slack({"status": status, "billing-active": "0"}) is False


@pytest.mark.parametrize(
    "bracket",
    [
        "卒",
        "卒 Guest",
        "アカウント重複",
        "職員",
        "研究員",
        "BLP",
        "他学科",
        "1",
        "1年",
        "TA",
        "院",
        "除籍",
        "退学",
        "M",
    ],
)
def test_ignores_non_grade_brackets_from_university_wide_export(bracket: str) -> None:
    # 全学ワークスペースのエクスポートには卒業生・他学科・提携企業ゲスト等の
    # データサイエンス学科と無関係な行が大量に混ざるため、既知の学年パターン
    # 以外はNoneを返し取り込まない。
    profile = parse_fullname(f"[{bracket}] 誰か / Someone", "someone@example.com")
    assert profile is None


@pytest.mark.asyncio
async def test_get_or_create_user_creates_then_updates(db_session) -> None:
    profile = parse_fullname(
        "[B1] 山田 太郎 / Taro Yamada", "s0000000-test@stu.musashino-u.ac.jp"
    )
    assert profile is not None

    user, created = await _get_or_create_user(
        db_session,
        email="s0000000-test@stu.musashino-u.ac.jp",
        slack_user_id="U0000000TEST",
        profile=profile,
    )
    assert created is True
    assert user.role == UserRole.student
    assert user.grade == "B1"

    # 進級後にfullnameが変わって再投入されるケース。
    updated_profile = parse_fullname(
        "[B2] 山田 太郎 / Taro Yamada", "s0000000-test@stu.musashino-u.ac.jp"
    )
    assert updated_profile is not None
    same_user, created_again = await _get_or_create_user(
        db_session,
        email="s0000000-test@stu.musashino-u.ac.jp",
        slack_user_id="U0000000TEST",
        profile=updated_profile,
    )
    assert created_again is False
    assert same_user.id == user.id
    assert same_user.grade == "B2"

    result = await db_session.execute(
        select(User).where(User.email == "s0000000-test@stu.musashino-u.ac.jp")
    )
    assert len(result.scalars().all()) == 1


@pytest.mark.asyncio
async def test_get_or_create_user_preserves_admin_role_on_update(db_session) -> None:
    # adminは運営が個別に付与する権限で、Slackエクスポートの学年ブラケットは
    # student/teacherしか表現できない。CSV再取り込みで既存adminの権限を
    # 勝手に落としてはいけない(実際に発生した事故)。
    admin = User(
        google_id="google-admin-test",
        email="s0000009-test@stu.musashino-u.ac.jp",
        name="運営 admin太郎",
        role=UserRole.admin,
        grade="B3",
    )
    db_session.add(admin)
    await db_session.flush()

    profile = parse_fullname(
        "[B4] 運営 admin太郎 / Admin Taro", "s0000009-test@stu.musashino-u.ac.jp"
    )
    assert profile is not None

    updated, created = await _get_or_create_user(
        db_session,
        email="s0000009-test@stu.musashino-u.ac.jp",
        slack_user_id="U0000009TEST",
        profile=profile,
    )

    assert created is False
    assert updated.role == UserRole.admin
    # role以外(進級等)は通常通り反映される。
    assert updated.grade == "B4"


def _row(
    *, email: str, fullname: str, status: str = "Member", userid: str | None = None
) -> dict[str, str]:
    return {
        "username": email.split("@")[0],
        "email": email,
        "status": status,
        "billing-active": "1",
        "has-2fa": "0",
        "has-sso": "0",
        # slack_user_idはDBでUNIQUE制約があるため、行ごとに一意な値にする。
        "userid": userid or f"U-{email.split('@')[0]}",
        "fullname": fullname,
        "displayname": fullname,
        "expiration-timestamp": "",
    }


@pytest.mark.asyncio
async def test_import_rows_creates_and_updates_users(db_session) -> None:
    existing_profile = parse_fullname(
        "[B1] 既存 花子 / Hanako Kison", "s0000005-test@stu.musashino-u.ac.jp"
    )
    assert existing_profile is not None
    await _get_or_create_user(
        db_session,
        email="s0000005-test@stu.musashino-u.ac.jp",
        slack_user_id="U0000005TEST",
        profile=existing_profile,
    )

    rows = [
        _row(
            email="s0000005-test@stu.musashino-u.ac.jp",
            fullname="[B2] 既存 花子 / Hanako Kison",
        ),
        _row(
            email="s0000006-test@stu.musashino-u.ac.jp",
            fullname="[B1] 新規 一郎 / Ichiro Shinki",
        ),
    ]

    summary = await import_rows(db_session, rows)

    assert summary.created == 1
    assert summary.updated == 1

    updated_user = (
        await db_session.execute(
            select(User).where(User.email == "s0000005-test@stu.musashino-u.ac.jp")
        )
    ).scalar_one()
    assert updated_user.grade == "B2"

    new_user = (
        await db_session.execute(
            select(User).where(User.email == "s0000006-test@stu.musashino-u.ac.jp")
        )
    ).scalar_one()
    assert new_user.grade == "B1"


@pytest.mark.asyncio
async def test_import_rows_records_skip_reasons(db_session) -> None:
    rows = [
        _row(
            email="deactivated-test@example.com",
            fullname="[B1] 退出済み 太郎 / Taro Taishutsu",
            status="Deactivated",
        ),
        _row(email="unparseable-test@example.com", fullname="山田 太郎"),
    ]

    summary = await import_rows(db_session, rows)

    assert summary.created == 0
    assert len(summary.skipped) == 2
    reasons_by_email = {s.email: s.reason for s in summary.skipped}
    assert "Deactivated" in reasons_by_email["deactivated-test@example.com"]
    assert "パース" in reasons_by_email["unparseable-test@example.com"]


@pytest.mark.asyncio
async def test_import_rows_deactivates_students_missing_from_csv(db_session) -> None:
    profile = parse_fullname(
        "[B4] 卒業予定 花子 / Hanako Sotsugyoyotei",
        "s0000007-test@stu.musashino-u.ac.jp",
    )
    assert profile is not None
    user, _ = await _get_or_create_user(
        db_session,
        email="s0000007-test@stu.musashino-u.ac.jp",
        slack_user_id="U0000007TEST",
        profile=profile,
    )
    assert user.is_active is True

    # 今年のCSVにこの学生は含まれない(=卒業/退学した)。
    rows = [
        _row(
            email="s0000008-test@stu.musashino-u.ac.jp",
            fullname="[B1] 在学 次郎 / Jiro Zaigaku",
        ),
    ]

    summary = await import_rows(db_session, rows)

    # 共有DBの実データも含めて非アクティブ化されるため、この学生1人だけとは
    # 限らない(1件以上であることのみ確認する)。
    assert summary.deactivated >= 1
    assert user.is_active is False


async def _existing_active_emails(db_session, *, exclude: str) -> set[str]:
    """テスト実行時点で既にDBにある(実データ含む)アクティブユーザーのメール。

    このリポジトリのテストは実Postgresを使い回すため(conftest.py参照)、
    active_emailsに含めないと対象外のユーザーまで巻き込んで非アクティブ化
    してしまう(rollbackされるため永続はしないが、テストの検証対象がぼやける)。

    CI等、他にデータが無いまっさらなDBだと exclude で唯一のアクティブ
    ユーザーを除いた瞬間に空集合になり、「CSVが空」の安全装置(全員を
    非アクティブ化しないためのガード)が誤発動してしまう。それを防ぐため、
    実データの有無によらず必ず1件以上になるダミーのメールを混ぜておく。
    """
    result = await db_session.execute(
        select(User.email).where(User.is_active.is_(True))
    )
    emails = set(result.scalars().all()) - {exclude}
    emails.add("placeholder-keep-non-empty@example.com")
    return emails


@pytest.mark.asyncio
async def test_deactivate_missing_users_deactivates_absent_student(
    db_session,
) -> None:
    profile = parse_fullname(
        "[B4] 卒業 太郎 / Taro Sotsugyo", "s0000001-test@stu.musashino-u.ac.jp"
    )
    assert profile is not None
    user, _ = await _get_or_create_user(
        db_session,
        email="s0000001-test@stu.musashino-u.ac.jp",
        slack_user_id="U0000001TEST",
        profile=profile,
    )
    assert user.is_active is True

    # 今年のCSVには他の全アクティブユーザーは含まれるが、この学生だけ
    # 含まれていない(=卒業/退学した)。
    other_active_emails = await _existing_active_emails(
        db_session, exclude="s0000001-test@stu.musashino-u.ac.jp"
    )
    deactivated = await _deactivate_missing_users(
        db_session, active_emails=other_active_emails
    )

    assert deactivated == 1
    assert user.is_active is False


@pytest.mark.asyncio
async def test_deactivate_missing_users_keeps_present_student_active(
    db_session,
) -> None:
    profile = parse_fullname(
        "[B2] 在学 次郎 / Jiro Zaigaku", "s0000002-test@stu.musashino-u.ac.jp"
    )
    assert profile is not None
    user, _ = await _get_or_create_user(
        db_session,
        email="s0000002-test@stu.musashino-u.ac.jp",
        slack_user_id="U0000002TEST",
        profile=profile,
    )

    active_emails = await _existing_active_emails(db_session, exclude="")
    active_emails.add("s0000002-test@stu.musashino-u.ac.jp")
    deactivated = await _deactivate_missing_users(
        db_session, active_emails=active_emails
    )

    assert deactivated == 0
    assert user.is_active is True


@pytest.mark.asyncio
async def test_deactivate_missing_users_never_touches_teachers(db_session) -> None:
    # 教員はSlackエクスポートに含まれない現役教員がいる実例が確認されたため、
    # Slack上のCSVに存在しなくても非アクティブ化してはいけない。
    profile = parse_fullname(
        "[教員] 現役 教授 / Gennyaku Kyoju", "teacher-not-in-slack@example.com"
    )
    assert profile is not None
    teacher, _ = await _get_or_create_user(
        db_session,
        email="teacher-not-in-slack@example.com",
        slack_user_id=None,
        profile=profile,
    )
    assert teacher.is_active is True

    # 教員のメールはactive_emailsに含めない(=Slackエクスポートに無い)。
    other_active_emails = await _existing_active_emails(
        db_session, exclude="teacher-not-in-slack@example.com"
    )
    deactivated = await _deactivate_missing_users(
        db_session, active_emails=other_active_emails
    )

    assert deactivated == 0
    assert teacher.is_active is True


@pytest.mark.asyncio
async def test_deactivate_missing_users_skips_when_no_active_emails(
    db_session,
) -> None:
    profile = parse_fullname(
        "[B3] 安全 花子 / Hanako Anzen", "s0000003-test@stu.musashino-u.ac.jp"
    )
    assert profile is not None
    user, _ = await _get_or_create_user(
        db_session,
        email="s0000003-test@stu.musashino-u.ac.jp",
        slack_user_id="U0000003TEST",
        profile=profile,
    )

    # active_emailsが空(CSVが空/パース失敗)の場合は、事故で全員を
    # 非アクティブ化しないようスキップする。
    deactivated = await _deactivate_missing_users(db_session, active_emails=set())

    assert deactivated == 0
    assert user.is_active is True


@pytest.mark.asyncio
async def test_reappearing_user_is_reactivated(db_session) -> None:
    profile = parse_fullname(
        "[B1] 復学 三郎 / Saburo Fukugaku", "s0000004-test@stu.musashino-u.ac.jp"
    )
    assert profile is not None
    user, _ = await _get_or_create_user(
        db_session,
        email="s0000004-test@stu.musashino-u.ac.jp",
        slack_user_id="U0000004TEST",
        profile=profile,
    )
    user.is_active = False
    await db_session.flush()

    # 翌年のCSVに再登場(復学)したケース。
    _, created_again = await _get_or_create_user(
        db_session,
        email="s0000004-test@stu.musashino-u.ac.jp",
        slack_user_id="U0000004TEST",
        profile=profile,
    )

    assert created_again is False
    assert user.is_active is True
