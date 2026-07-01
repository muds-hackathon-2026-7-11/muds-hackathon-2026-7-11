import logging
import os

from dotenv import load_dotenv
from slack_bolt.adapter.socket_mode import SocketModeHandler

from slack_bot.app import create_app


def main() -> None:
    load_dotenv()
    logging.basicConfig(level=logging.INFO)
    SocketModeHandler(create_app(), os.environ["SLACK_APP_TOKEN"]).start()
