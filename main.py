import os
import re

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
PERSONAL_CHANNEL_ID = os.getenv("PERSONAL_CHANNEL_ID")
PERSONAL_USERGROUP_ID = os.getenv("PERSONAL_USERGROUP_ID")

app = App(token=SLACK_BOT_TOKEN)

# Sentry so good bruh
sentry_sdk.init(
    dsn=SENTRY_DSN,
    enable_logs=True,
)


# Auto-Thread feature
@app.message()
def check_for_ping_msgs(message, client, logger):

    text = message.get("text", "")

    has_here = "<!here>" in text or "@here" in text
    has_channel = "<!channel>" in text or "@channel" in text
    has_usergroup = f"<!subteam^{PERSONAL_USERGROUP_ID}" in text

    if has_here or has_channel or has_usergroup:
        logger.info(f"Mention detected OwO {text}")
        try:
            client.chat_postMessage(channel=message.get("channel"), text=":thread:")
        except Exception as e:
            sentry_sdk.capture_exception(e)


@app.command("/join-the-padded-room")
def joining_guardian(ack, respond, say, command, client):
    ack()

    user_id = command["user_id"]

    members_response = client.conversations_members(channel=PERSONAL_CHANNEL_ID)
    members = members_response["members"]

    if user_id in members:
        respond(f"you are already in {PERSONAL_CHANNEL_ID}, you goober :neocat_blank:")
        return

    client.chat_postMessage(
        channel=user_id,
        text=f":mhm:, <@{user_id}>. you requested access to join the padded room. The manager of the padded room shall review your request in the next working hour :nodnod:",
    )

    response = requests.get(HCA_API_URL, params={"slack_id": user_id})
    idv_data = response.json()
    idv_result = idv_data.get("result")
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
                "text": f"🐱 User: {user_id}",
                "emoji": True,
            },
        },
        {
            "type": "section",
            "text": {"type": "plain_text", "text": "📅 Date Joined:", "emoji": True},
        },
        {
            "type": "section",
            "text": {
                "type": "plain_text",
                "text": f"🛂 IDV Status: {idv_result}",
                "emoji": True,
            },
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
                    "value": user_id,
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
                    "value": user_id,
                    "action_id": "actionId-1",
                }
            ],
        },
    ]

    client.chat_postMessage(
        channel=CMAN_USER_ID,
        text="New PC Request",
        blocks=blocks,
    )


# app home
@app.event("app_home_opened")
def update_home_tab(client, event):
    user_id = event["user"]

    members_response = client.conversations_members(channel=PERSONAL_CHANNEL_ID)
    members = members_response["members"]

    is_member = user_id in members

    if is_member:
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"you are already in <#{PERSONAL_CHANNEL_ID}>, you goober! :neocat_happy:",
                },
            },
        ]
    else:
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"it seems like you haven't joined <#{PERSONAL_CHANNEL_ID}>, you want to join that channel? :neocat_wink_blep:",
                },
            },
            {"type": "divider"},
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "join channel",
                            "emoji": True,
                        },
                        "style": "primary",
                        "value": "coolbutton",
                        "action_id": "join_pc_button_home",
                    }
                ],
            },
        ]

    client.views_publish(
        user_id=user_id,
        view={
            "type": "home",
            "blocks": blocks,
        },
    )


@app.action("join_pc_button_home")
# This is the same logic for joining_guardian :3
def handle_join_button_app_home(ack, respond, say, command, client):
    ack()

    user_id = command["user_id"]

    members_response = client.conversations_members(channel=PERSONAL_CHANNEL_ID)
    members = members_response["members"]

    if user_id in members:
        respond(f"you are already in {PERSONAL_CHANNEL_ID}, you goober :neocat_blank:")
        return

    client.chat_postMessage(
        channel=user_id,
        text=f":mhm:, <@{user_id}>. you requested access to join the padded room. The manager of the padded room shall review your request in the next working hour :nodnod:",
    )

    response = requests.get(HCA_API_URL, params={"slack_id": user_id})
    idv_data = response.json()
    idv_result = idv_data.get("result")
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
                "text": f"🐱 User: {user_id}",
                "emoji": True,
            },
        },
        {
            "type": "section",
            "text": {"type": "plain_text", "text": "📅 Date Joined:", "emoji": True},
        },
        {
            "type": "section",
            "text": {
                "type": "plain_text",
                "text": f"🛂 IDV Status: {idv_result}",
                "emoji": True,
            },
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
                    "value": user_id,
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
                    "value": user_id,
                    "action_id": "actionId-1",
                }
            ],
        },
    ]

    client.chat_postMessage(
        channel=CMAN_USER_ID,
        text="New PC Request",
        blocks=blocks,
    )


@app.action("accept_pc_action")
def handle_accept_button(ack, body, client):
    ack()

    requestor_user_id = body["actions"][0]["value"]

    client.chat_update(
        channel=body["channel"]["id"],
        ts=body["message"]["ts"],
        text=f"Accepted request for <@{requestor_user_id}>!",
        blocks=[
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"Accepted request for <@{requestor_user_id}>!",
                },
            }
        ],
    )

    client.conversations_invite(channel=PERSONAL_CHANNEL_ID, users=requestor_user_id)

    group_info = client.usergroups_user_list(usergroup=PERSONAL_USERGROUP_ID)
    current_users = group_info.get("users", [])

    if requestor_user_id not in current_users:
        current_users.append(requestor_user_id)
        client.usergroups_users_update(
            usergroup=PERSONAL_USERGROUP_ID, users=",".join(current_users)
        )

    client.chat_postMessage(
        channel=requestor_user_id,
        text=f"Yaay! Your request to join <@{CMAN_USER_ID}>'s personal channel has been accepted! Now have fun in the channel! :yay:",
    )


@app.action("deny_pc_action")
def handle_deny_button(ack, body, client, logger):
    ack()

    user_id = body["actions"][0]["value"]

    client.chat_postMessage(
        channel=user_id,
        text="hi <@user_id>. your request to the padded room has been denied. if you think this is a mistake, please resend your request! :(",
    )


if __name__ == "__main__":
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()
