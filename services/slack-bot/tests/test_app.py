import json
from unittest.mock import MagicMock, patch

import httpx
from slack_sdk.errors import SlackApiError

from slack_bot.app import (
    _handle_answer_action,
    _handle_answer_view_submission,
    _handle_global_error,
    _handle_question_action,
    _handle_question_view_submission,
)


def _slack_api_error(message: str = "boom") -> SlackApiError:
    return SlackApiError(message, MagicMock())


def _action_body(user_id: str = "U123", trigger_id: str = "T1") -> dict:
    return {"user": {"id": user_id}, "trigger_id": trigger_id}


def _button_action_body(
    value: str,
    user_id: str = "U123",
    trigger_id: str = "T1",
    channel_id: str = "D1",
    message_ts: str = "111.222",
) -> dict:
    return {
        "user": {"id": user_id},
        "trigger_id": trigger_id,
        "actions": [{"value": value}],
        "channel": {"id": channel_id},
        "message": {"ts": message_ts},
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


def _answer_view(
    question_id: str = "q1",
    content: str = "回答です",
    channel_id: str = "D1",
    message_ts: str = "111.222",
) -> dict:
    private_metadata = json.dumps(
        {"question_id": question_id, "channel_id": channel_id, "message_ts": message_ts}
    )
    return {
        "private_metadata": private_metadata,
        "state": {"values": {"content_block": {"content_input": {"value": content}}}},
    }


def _client_with_opened_view(view_id: str = "V1") -> MagicMock:
    client = MagicMock()
    client.views_open.return_value = {"view": {"id": view_id}}
    return client


def test_question_action_opens_loading_modal_immediately() -> None:
    ack = MagicMock()
    client = _client_with_opened_view()
    with patch(
        "slack_bot.app.fetch_seminars",
        return_value=[{"id": "s1", "name": "AIゼミ"}],
    ):
        _handle_question_action(ack, _action_body(), client)

    ack.assert_called_once()
    # trigger_idを消費するviews_openは、自前APIへの問い合わせより前に
    # (読み込み中のモーダルとして)即座に呼ばれる。
    assert client.views_open.call_args.kwargs["trigger_id"] == "T1"


def test_question_action_updates_modal_with_seminars_after_fetch() -> None:
    ack = MagicMock()
    client = _client_with_opened_view("V1")
    with patch(
        "slack_bot.app.fetch_seminars",
        return_value=[{"id": "s1", "name": "AIゼミ"}],
    ):
        _handle_question_action(ack, _action_body(), client)

    client.views_update.assert_called_once()
    assert client.views_update.call_args.kwargs["view_id"] == "V1"
    view = client.views_update.call_args.kwargs["view"]
    assert view["callback_id"] == "question_submit"


def test_question_action_updates_modal_with_message_when_no_seminars() -> None:
    ack = MagicMock()
    client = _client_with_opened_view("V1")
    with patch("slack_bot.app.fetch_seminars", return_value=[]):
        _handle_question_action(ack, _action_body(), client)

    view = client.views_update.call_args.kwargs["view"]
    assert "現在登録されているゼミがありません" in view["blocks"][0]["text"]["text"]


def test_question_action_updates_modal_with_message_on_api_error() -> None:
    ack = MagicMock()
    client = _client_with_opened_view("V1")
    with patch("slack_bot.app.fetch_seminars", side_effect=httpx.ConnectError("boom")):
        _handle_question_action(ack, _action_body(), client)

    view = client.views_update.call_args.kwargs["view"]
    assert "取得に失敗" in view["blocks"][0]["text"]["text"]


def test_question_action_does_not_call_api_when_loading_modal_fails_to_open() -> None:
    ack = MagicMock()
    client = MagicMock()
    client.views_open.side_effect = _slack_api_error("trigger_id_expired")
    with patch("slack_bot.app.fetch_seminars") as fetch_seminars:
        _handle_question_action(ack, _action_body(), client)

    fetch_seminars.assert_not_called()
    client.views_update.assert_not_called()


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
    _handle_answer_action(
        ack, _button_action_body("q1", channel_id="D1", message_ts="111.222"), client
    )

    ack.assert_called_once()
    client.views_open.assert_called_once()
    assert client.views_open.call_args.kwargs["trigger_id"] == "T1"
    view = client.views_open.call_args.kwargs["view"]
    metadata = json.loads(view["private_metadata"])
    assert metadata == {
        "question_id": "q1",
        "channel_id": "D1",
        "message_ts": "111.222",
    }


def test_answer_action_does_not_raise_when_modal_fails_to_open() -> None:
    ack = MagicMock()
    client = MagicMock()
    client.views_open.side_effect = _slack_api_error("trigger_id_expired")

    _handle_answer_action(
        ack, _button_action_body("q1", channel_id="D1", message_ts="111.222"), client
    )

    ack.assert_called_once()


def test_answer_view_submission_sends_success_message_on_201() -> None:
    ack = MagicMock()
    client = MagicMock()
    response = MagicMock(status_code=201)
    with patch("slack_bot.app.submit_answer", return_value=response):
        _handle_answer_view_submission(
            ack,
            _action_body(),
            _answer_view(channel_id="D1", message_ts="111.222"),
            client,
        )

    ack.assert_called_once()
    call_kwargs = client.chat_postMessage.call_args.kwargs
    assert call_kwargs["channel"] == "D1"
    assert call_kwargs["thread_ts"] == "111.222"
    assert "送信しました" in call_kwargs["text"]


def test_answer_view_submission_shows_error_on_malformed_metadata() -> None:
    ack = MagicMock()
    client = MagicMock()
    broken_view = {
        "private_metadata": "not-json",
        "state": {"values": {"content_block": {"content_input": {"value": "回答"}}}},
    }
    _handle_answer_view_submission(ack, _action_body(), broken_view, client)

    ack.assert_called_once()
    text = client.chat_postMessage.call_args.kwargs["text"]
    assert "失敗" in text


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


def test_global_error_handler_logs_the_exception() -> None:
    logger = MagicMock()

    _handle_global_error(ValueError("boom"), _action_body(), logger)

    logger.exception.assert_called_once()
