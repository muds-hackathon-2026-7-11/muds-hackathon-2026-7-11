from unittest.mock import MagicMock, patch

import httpx

from slack_bot.app import (
    _handle_answer_action,
    _handle_answer_view_submission,
    _handle_question_action,
    _handle_question_view_submission,
)


def _action_body(user_id: str = "U123", trigger_id: str = "T1") -> dict:
    return {"user": {"id": user_id}, "trigger_id": trigger_id}


def _button_action_body(
    value: str, user_id: str = "U123", trigger_id: str = "T1"
) -> dict:
    return {
        "user": {"id": user_id},
        "trigger_id": trigger_id,
        "actions": [{"value": value}],
    }


def _view(seminar_id: str = "s1", content: str = "質問です") -> dict:
    return {
        "state": {
            "values": {
                "seminar_block": {
                    "seminar_select": {"selected_option": {"value": seminar_id}}
                },
                "content_block": {"content_input": {"value": content}},
            }
        }
    }


def _answer_view(question_id: str = "q1", content: str = "回答です") -> dict:
    return {
        "private_metadata": question_id,
        "state": {"values": {"content_block": {"content_input": {"value": content}}}},
    }


def test_question_action_opens_modal_when_seminars_exist() -> None:
    ack = MagicMock()
    client = MagicMock()
    with patch(
        "slack_bot.app.fetch_seminars",
        return_value=[{"id": "s1", "name": "AIゼミ"}],
    ):
        _handle_question_action(ack, _action_body(), client)

    ack.assert_called_once()
    client.views_open.assert_called_once()
    assert client.views_open.call_args.kwargs["trigger_id"] == "T1"
    client.chat_postEphemeral.assert_not_called()


def test_question_action_shows_ephemeral_message_when_no_seminars() -> None:
    ack = MagicMock()
    client = MagicMock()
    with patch("slack_bot.app.fetch_seminars", return_value=[]):
        _handle_question_action(ack, _action_body(), client)

    client.views_open.assert_not_called()
    client.chat_postEphemeral.assert_called_once()


def test_question_action_shows_ephemeral_message_on_api_error() -> None:
    ack = MagicMock()
    client = MagicMock()
    with patch("slack_bot.app.fetch_seminars", side_effect=httpx.ConnectError("boom")):
        _handle_question_action(ack, _action_body(), client)

    client.views_open.assert_not_called()
    client.chat_postEphemeral.assert_called_once()


def test_view_submission_sends_success_message_on_201() -> None:
    ack = MagicMock()
    client = MagicMock()
    response = MagicMock(status_code=201)
    with patch("slack_bot.app.submit_question", return_value=response):
        _handle_question_view_submission(ack, _action_body(), _view(), client)

    ack.assert_called_once()
    text = client.chat_postMessage.call_args.kwargs["text"]
    assert "送信しました" in text


def test_view_submission_shows_api_detail_message_on_404() -> None:
    ack = MagicMock()
    client = MagicMock()
    response = MagicMock(status_code=404)
    response.json.return_value = {"detail": "先にログインしてください"}
    with patch("slack_bot.app.submit_question", return_value=response):
        _handle_question_view_submission(ack, _action_body(), _view(), client)

    text = client.chat_postMessage.call_args.kwargs["text"]
    assert text == "先にログインしてください"


def test_view_submission_shows_generic_error_on_unexpected_status() -> None:
    ack = MagicMock()
    client = MagicMock()
    response = MagicMock(status_code=500, text="boom")
    with patch("slack_bot.app.submit_question", return_value=response):
        _handle_question_view_submission(ack, _action_body(), _view(), client)

    text = client.chat_postMessage.call_args.kwargs["text"]
    assert "失敗" in text


def test_view_submission_shows_generic_error_on_connection_failure() -> None:
    ack = MagicMock()
    client = MagicMock()
    with patch("slack_bot.app.submit_question", side_effect=httpx.ConnectError("boom")):
        _handle_question_view_submission(ack, _action_body(), _view(), client)

    text = client.chat_postMessage.call_args.kwargs["text"]
    assert "失敗" in text


def test_answer_action_opens_modal_with_question_id() -> None:
    ack = MagicMock()
    client = MagicMock()
    _handle_answer_action(ack, _button_action_body("q1"), client)

    ack.assert_called_once()
    client.views_open.assert_called_once()
    assert client.views_open.call_args.kwargs["trigger_id"] == "T1"
    view = client.views_open.call_args.kwargs["view"]
    assert view["private_metadata"] == "q1"


def test_answer_view_submission_sends_success_message_on_201() -> None:
    ack = MagicMock()
    client = MagicMock()
    response = MagicMock(status_code=201)
    with patch("slack_bot.app.submit_answer", return_value=response):
        _handle_answer_view_submission(ack, _action_body(), _answer_view(), client)

    ack.assert_called_once()
    text = client.chat_postMessage.call_args.kwargs["text"]
    assert "送信しました" in text


def test_answer_view_submission_shows_api_detail_message_on_404() -> None:
    ack = MagicMock()
    client = MagicMock()
    response = MagicMock(status_code=404)
    response.json.return_value = {"detail": "指定された質問が見つかりません。"}
    with patch("slack_bot.app.submit_answer", return_value=response):
        _handle_answer_view_submission(ack, _action_body(), _answer_view(), client)

    text = client.chat_postMessage.call_args.kwargs["text"]
    assert text == "指定された質問が見つかりません。"


def test_answer_view_submission_shows_generic_error_on_unexpected_status() -> None:
    ack = MagicMock()
    client = MagicMock()
    response = MagicMock(status_code=500, text="boom")
    with patch("slack_bot.app.submit_answer", return_value=response):
        _handle_answer_view_submission(ack, _action_body(), _answer_view(), client)

    text = client.chat_postMessage.call_args.kwargs["text"]
    assert "失敗" in text


def test_answer_view_submission_shows_generic_error_on_connection_failure() -> None:
    ack = MagicMock()
    client = MagicMock()
    with patch("slack_bot.app.submit_answer", side_effect=httpx.ConnectError("boom")):
        _handle_answer_view_submission(ack, _action_body(), _answer_view(), client)

    text = client.chat_postMessage.call_args.kwargs["text"]
    assert "失敗" in text
