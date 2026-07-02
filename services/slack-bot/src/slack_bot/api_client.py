import os

import httpx

API_BASE_URL = os.environ.get("API_BASE_URL", "http://api:8000")


def fetch_seminars() -> list[dict]:
    response = httpx.get(f"{API_BASE_URL}/seminars", timeout=5.0)
    response.raise_for_status()
    seminars: list[dict] = response.json()
    return seminars


def submit_question(
    *, seminar_id: str, slack_user_id: str, content: str
) -> httpx.Response:
    return httpx.post(
        f"{API_BASE_URL}/questions",
        json={
            "seminar_id": seminar_id,
            "slack_user_id": slack_user_id,
            "content": content,
        },
        timeout=5.0,
    )
