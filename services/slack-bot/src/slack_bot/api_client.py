import os

import httpx

API_BASE_URL = os.environ.get("API_BASE_URL", "http://api:8000")
INTERNAL_API_SECRET = os.environ.get("INTERNAL_API_SECRET", "")


def fetch_seminars() -> list[dict]:
    # Slack Botはログイン中の学生セッションを持たないため、通常のGET /seminars
    # (JWT必須)ではなくrequire_internal_secretで認証する専用エンドポイントを叩く。
    response = httpx.get(
        f"{API_BASE_URL}/seminars/for-slack-bot",
        headers={"X-Internal-Secret": INTERNAL_API_SECRET},
        timeout=5.0,
    )
    response.raise_for_status()
    seminars: list[dict] = response.json()
    return seminars


def submit_question(
    *, seminar_id: str, slack_user_id: str, content: str
) -> httpx.Response:
    # slack_user_id自体は秘密情報ではないため、fetch_seminarsと同じく
    # require_internal_secretで「Bot経由の呼び出しであること」を保証する(#170)。
    return httpx.post(
        f"{API_BASE_URL}/questions",
        json={
            "seminar_id": seminar_id,
            "slack_user_id": slack_user_id,
            "content": content,
        },
        headers={"X-Internal-Secret": INTERNAL_API_SECRET},
        timeout=5.0,
    )


def submit_answer(
    *, question_id: str, slack_user_id: str, content: str
) -> httpx.Response:
    return httpx.post(
        f"{API_BASE_URL}/answers",
        json={
            "question_id": question_id,
            "slack_user_id": slack_user_id,
            "content": content,
        },
        headers={"X-Internal-Secret": INTERNAL_API_SECRET},
        timeout=5.0,
    )
