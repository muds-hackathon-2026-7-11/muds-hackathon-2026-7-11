from slack_bot.app import create_app


def test_create_app_builds_without_error(monkeypatch) -> None:
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-test-token")
    app = create_app(token_verification_enabled=False)
    assert app is not None
