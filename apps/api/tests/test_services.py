import pytest

from api.services import normalize_grade


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("B1", "B1"),
        ("B2", "B2"),
        ("B3", "B3"),
        ("B4", "B4"),
        # MIDS学生も末尾のB1〜B4として扱う(#99)。
        ("MIDS/B1", "B1"),
        ("MIDS/B3", "B3"),
        ("MIDS/B4", "B4"),
        # 大学院生・guest・空文字・未設定はB1〜B4のどれにも一致しない。
        ("M1", None),
        ("M1 guest", None),
        ("M2", None),
        ("M2 guest", None),
        ("D1", None),
        ("", None),
        (None, None),
    ],
)
def test_normalize_grade(raw: str | None, expected: str | None) -> None:
    assert normalize_grade(raw) == expected
