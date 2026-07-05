import pytest
from sqlalchemy import select

from api.import_users import _get_or_create_user, parse_fullname
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
    profile = parse_fullname("山田 太郎", "s2622014@stu.musashino-u.ac.jp")
    assert profile is None


@pytest.mark.asyncio
async def test_get_or_create_user_creates_then_updates(db_session) -> None:
    profile = parse_fullname(
        "[B1] 山田 太郎 / Taro Yamada", "s2622014@stu.musashino-u.ac.jp"
    )
    assert profile is not None

    user, created = await _get_or_create_user(
        db_session,
        email="s2622014@stu.musashino-u.ac.jp",
        slack_user_id="U0AR0GQK3PD",
        profile=profile,
    )
    assert created is True
    assert user.role == UserRole.student
    assert user.grade == "B1"

    # 進級後にfullnameが変わって再投入されるケース。
    updated_profile = parse_fullname(
        "[B2] 山田 太郎 / Taro Yamada", "s2622014@stu.musashino-u.ac.jp"
    )
    assert updated_profile is not None
    same_user, created_again = await _get_or_create_user(
        db_session,
        email="s2622014@stu.musashino-u.ac.jp",
        slack_user_id="U0AR0GQK3PD",
        profile=updated_profile,
    )
    assert created_again is False
    assert same_user.id == user.id
    assert same_user.grade == "B2"

    result = await db_session.execute(
        select(User).where(User.email == "s2622014@stu.musashino-u.ac.jp")
    )
    assert len(result.scalars().all()) == 1
