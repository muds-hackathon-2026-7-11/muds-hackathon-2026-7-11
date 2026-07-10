from unittest.mock import patch

from slack_bot.app import _LISTENER_MAX_WORKERS, create_app


def test_create_app_builds_without_error(monkeypatch) -> None:
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-test-token")
    app = create_app(token_verification_enabled=False)
    assert app is not None


def test_create_app_configures_a_larger_listener_thread_pool(monkeypatch) -> None:
    # Boltのデフォルト(max_workers=5)だと、同時に5件処理中の間は6件目以降が
    # ack期限に間に合わずボタンが無反応に見える(#173)。
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-test-token")
    with patch("slack_bot.app.App") as mock_app_cls:
        create_app(token_verification_enabled=False)

    _, kwargs = mock_app_cls.call_args
    executor = kwargs["listener_executor"]
    assert executor._max_workers == _LISTENER_MAX_WORKERS
    assert _LISTENER_MAX_WORKERS > 5
