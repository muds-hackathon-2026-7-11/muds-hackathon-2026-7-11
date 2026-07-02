import logging
import os
import sys

from dotenv import load_dotenv
from slack_bolt.adapter.socket_mode import SocketModeHandler

from slack_bot.app import create_app

logger = logging.getLogger(__name__)

REQUIRED_ENV_VARS = ("SLACK_BOT_TOKEN", "SLACK_APP_TOKEN")


def main() -> None:
    load_dotenv()
    logging.basicConfig(level=logging.INFO)

    missing = [name for name in REQUIRED_ENV_VARS if not os.environ.get(name)]
    if missing:
        logger.error(
            "Slack Botを起動できません。.envに %s を設定してください。",
            ", ".join(missing),
        )
        sys.exit(1)

    SocketModeHandler(create_app(), os.environ["SLACK_APP_TOKEN"]).start()
