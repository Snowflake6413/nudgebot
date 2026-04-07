import os

import requests
import sentry_sdk
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

load_dotenv()


# Env
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN")
SENTRY_DSN = os.getenv("SENTRY_DSN")
HCA_API_URL = os.getenv("HCA_API_URL")
CMAN_USER_ID = os.getenv("CMAN_USER_ID")

app = App(token=SLACK_BOT_TOKEN)

# Sentry so good bruh
sentry_sdk.init(
    dsn=SENTRY_DSN,
    enable_logs=True,
)


@app.command("/join-the-padded-room")
def joining_guardian(ack, respond, say, command, client):
    ack()

    user_id = command["user_id"]

    client.chat_postMessage(
        channel=user_id,
        text=f":mhm:, {user_id}. you requested access to join the padded room. The manager of the padded room shall review your request in the next working hour :nodnod:",
    )

    idv_response = requests.get(HCA_API_URL, params={"slack_id": user_id})

    blocks = [
        {
            "type": "section",
            "text": {
                "type": "plain_text",
                "text": "New request to the padded room:tm:",
                "emoji": True,
            },
        },
        {
            "type": "section",
            "text": {
                "type": "plain_text",
                "text": "🐱 User: <user_id_goes_here>",
                "emoji": True,
            },
        },
        {
            "type": "section",
            "text": {"type": "plain_text", "text": "📅 Date Joined:", "emoji": True},
        },
        {
            "type": "section",
            "text": {"type": "plain_text", "text": "🛂 IDV Status:", "emoji": True},
        },
        {"type": "divider"},
        {
            "type": "context",
            "elements": [
                {
                    "type": "plain_text",
                    "text": "do you accept or deny? OwO",
                    "emoji": True,
                }
            ],
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Accept", "emoji": True},
                    "style": "primary",
                    "value": "click_me_123",
                    "action_id": "actionId-0",
                }
            ],
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Deny", "emoji": True},
                    "style": "danger",
                    "value": "click_me_123",
                    "action_id": "actionId-0",
                }
            ],
        },
    ]
