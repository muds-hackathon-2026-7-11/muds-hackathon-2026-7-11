import json
import logging
import os

import httpx
from slack_bolt import App
from slack_sdk.errors import SlackApiError

from slack_bot.api_client import fetch_seminars, submit_answer, submit_question

logger = logging.getLogger(__name__)


def _home_view() -> dict:
    web_app_url = os.environ.get("WEB_APP_URL", "http://localhost:3100")
    return {
        "type": "home",
        "blocks": [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "🎓 ゼミナビ"},
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": "ゼミ選択をサポートします"},
            },
            {"type": "divider"},
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "🌐 アプリを開く"},
                        "url": web_app_url,
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "💬 質問する"},
                        "action_id": "question",
                    },
                ],
            },
        ],
    }


def _question_modal_view(seminars: list[dict]) -> dict:
    seminar_options = [
        {
            "text": {"type": "plain_text", "text": seminar["name"]},
            "value": seminar["id"],
        }
        for seminar in seminars
    ]
    return {
        "type": "modal",
        "callback_id": "question_submit",
        "title": {"type": "plain_text", "text": "質問する"},
        "submit": {"type": "plain_text", "text": "送信"},
        "close": {"type": "plain_text", "text": "キャンセル"},
        "blocks": [
            {
                "type": "input",
                "block_id": "seminar_block",
                "label": {"type": "plain_text", "text": "ゼミを選択"},
                "element": {
                    "type": "static_select",
                    "action_id": "seminar_select",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "ゼミを選んでください",
                    },
                    "options": seminar_options,
                },
            },
            {
                "type": "input",
                "block_id": "content_block",
                "label": {"type": "plain_text", "text": "質問内容"},
                "element": {
                    "type": "plain_text_input",
                    "action_id": "content_input",
                    "multiline": True,
                    "min_length": 1,
                    "max_length": 2000,
                },
            },
        ],
    }


def _loading_modal_view(title: str) -> dict:
    return {
        "type": "modal",
        "callback_id": "loading",
        "title": {"type": "plain_text", "text": title},
        "close": {"type": "plain_text", "text": "閉じる"},
        "blocks": [
            {"type": "section", "text": {"type": "mrkdwn", "text": "読み込み中..."}},
        ],
    }


def _message_modal_view(title: str, message: str) -> dict:
    return {
        "type": "modal",
        "callback_id": "message",
        "title": {"type": "plain_text", "text": title},
        "close": {"type": "plain_text", "text": "閉じる"},
        "blocks": [
            {"type": "section", "text": {"type": "mrkdwn", "text": message}},
        ],
    }


def _answer_modal_view(question_id: str, channel_id: str, message_ts: str) -> dict:
    private_metadata = json.dumps(
        {
            "question_id": question_id,
            "channel_id": channel_id,
            "message_ts": message_ts,
        }
    )
    return {
        "type": "modal",
        "callback_id": "answer_submit",
        "private_metadata": private_metadata,
        "title": {"type": "plain_text", "text": "回答する"},
        "submit": {"type": "plain_text", "text": "送信"},
        "close": {"type": "plain_text", "text": "キャンセル"},
        "blocks": [
            {
                "type": "input",
                "block_id": "content_block",
                "label": {"type": "plain_text", "text": "回答内容"},
                "element": {
                    "type": "plain_text_input",
                    "action_id": "content_input",
                    "multiline": True,
                    "min_length": 1,
                    "max_length": 2000,
                },
            },
        ],
    }


def _handle_home_opened(client, event) -> None:
    client.views_publish(user_id=event["user"], view=_home_view())


def _safe_views_update(client, *, view_id: str, view: dict) -> None:
    try:
        client.views_update(view_id=view_id, view=view)
    except SlackApiError:
        logger.exception("failed to update modal view_id=%s", view_id)


def _handle_question_action(ack, body, client) -> None:
    """「💬 質問する」ボタン押下時のハンドラ。

    Boltのデコレータの外に切り出してあるのは、`client`/`ack`をMockに差し替えて
    ユニットテストしやすくするため(create_app内に閉じ込めるとテストできない)。

    trigger_idは発行から3秒しか有効でなく、1回しか使えない。fetch_seminars
    (自前APIへのHTTP呼び出し)をtrigger_idの消費(views_open)より前に置くと、
    API側が少し遅いだけでtrigger_id_expiredになりモーダルが開かずボタンが
    無反応に見えてしまう。そのため、まず読み込み中のモーダルをtrigger_idで
    即座に開き、内容が揃ってからviews_updateで差し替える。
    """
    ack()
    try:
        opened = client.views_open(
            trigger_id=body["trigger_id"], view=_loading_modal_view("質問する")
        )
    except SlackApiError:
        logger.exception("failed to open loading modal for question action")
        return
    view_id = opened["view"]["id"]

    try:
        seminars = fetch_seminars()
    except httpx.HTTPError:
        logger.exception("failed to fetch seminars from API")
        _safe_views_update(
            client,
            view_id=view_id,
            view=_message_modal_view(
                "質問する",
                "ゼミ情報の取得に失敗しました。時間をおいて再度お試しください。",
            ),
        )
        return

    if not seminars:
        _safe_views_update(
            client,
            view_id=view_id,
            view=_message_modal_view(
                "質問する", "現在登録されているゼミがありません。"
            ),
        )
        return

    _safe_views_update(client, view_id=view_id, view=_question_modal_view(seminars))


def _handle_question_view_submission(ack, body, view, client) -> None:
    ack()
    user_id = body["user"]["id"]
    values = view["state"]["values"]
    seminar_id = values["seminar_block"]["seminar_select"]["selected_option"]["value"]
    content = values["content_block"]["content_input"]["value"]

    try:
        response = submit_question(
            seminar_id=seminar_id, slack_user_id=user_id, content=content
        )
    except httpx.HTTPError:
        logger.exception("failed to submit question to API")
        client.chat_postMessage(
            channel=user_id,
            text="送信に失敗しました。時間をおいて再度お試しください。",
        )
        return

    if response.status_code == 201:
        client.chat_postMessage(
            channel=user_id,
            text=(
                ":white_check_mark: *質問を送信しました*\n"
                f">{content}\n\n"
                "回答が届いたら通知します。"
            ),
        )
    elif response.status_code == 404:
        client.chat_postMessage(
            channel=user_id,
            text=response.json().get("detail", "送信に失敗しました。"),
        )
    else:
        logger.error(
            "unexpected API response: status=%s body=%s",
            response.status_code,
            response.text,
        )
        client.chat_postMessage(
            channel=user_id,
            text="送信に失敗しました。時間をおいて再度お試しください。",
        )


def _handle_answer_action(ack, body, client) -> None:
    """通知DM内の「回答する」ボタン押下時のハンドラ。

    元のメッセージのchannel_id/message_tsをモーダルに持ち回り、送信成功時に
    自分自身の回答もそのメッセージへのスレッド返信として表示できるようにする。
    """
    ack()
    question_id = body["actions"][0]["value"]
    channel_id = body["channel"]["id"]
    message_ts = body["message"]["ts"]
    try:
        client.views_open(
            trigger_id=body["trigger_id"],
            view=_answer_modal_view(question_id, channel_id, message_ts),
        )
    except SlackApiError:
        logger.exception("failed to open answer modal")


def _handle_answer_view_submission(ack, body, view, client) -> None:
    ack()
    user_id = body["user"]["id"]

    try:
        metadata = json.loads(view["private_metadata"])
        question_id = metadata["question_id"]
        channel_id = metadata["channel_id"]
        message_ts = metadata["message_ts"]
        content = view["state"]["values"]["content_block"]["content_input"]["value"]
    except (json.JSONDecodeError, KeyError):
        logger.exception("failed to parse answer modal metadata")
        client.chat_postMessage(
            channel=user_id,
            text="送信に失敗しました。時間をおいて再度お試しください。",
        )
        return

    try:
        response = submit_answer(
            question_id=question_id, slack_user_id=user_id, content=content
        )
    except httpx.HTTPError:
        logger.exception("failed to submit answer to API")
        client.chat_postMessage(
            channel=user_id,
            text="送信に失敗しました。時間をおいて再度お試しください。",
        )
        return

    if response.status_code == 201:
        client.chat_postMessage(
            channel=channel_id,
            thread_ts=message_ts,
            text=f":white_check_mark: *回答を送信しました*\n>{content}",
        )
    elif response.status_code == 404:
        client.chat_postMessage(
            channel=user_id,
            text=response.json().get("detail", "送信に失敗しました。"),
        )
    else:
        logger.error(
            "unexpected API response: status=%s body=%s",
            response.status_code,
            response.text,
        )
        client.chat_postMessage(
            channel=user_id,
            text="送信に失敗しました。時間をおいて再度お試しください。",
        )


def _handle_global_error(error, body, logger) -> None:
    """未処理の例外を必ずログに残すためのフォールバック。

    個別ハンドラでcatchし損ねた例外(SlackApiError以外の予期しないものも
    含む)がここで握りつぶされて何のログも残らない、という事態を防ぐ。
    """
    logger.exception("unhandled error in listener: %s (body=%s)", error, body)


def create_app(token_verification_enabled: bool = True) -> App:
    """Build the Bolt App and register all handlers.

    App構築はこの中で行う(モジュールimport時点ではSLACK_BOT_TOKENを要求しないため)。
    token_verification_enabled=Falseにすると、Boltの起動時auth.test呼び出しをスキップできる(テスト用)。
    """
    app = App(
        token=os.environ["SLACK_BOT_TOKEN"],
        token_verification_enabled=token_verification_enabled,
    )

    app.event("app_home_opened")(_handle_home_opened)
    app.action("question")(_handle_question_action)
    app.view("question_submit")(_handle_question_view_submission)
    app.action("answer_question")(_handle_answer_action)
    app.view("answer_submit")(_handle_answer_view_submission)
    app.error(_handle_global_error)

    return app
