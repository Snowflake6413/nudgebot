import os
import re
import sqlite3
import threading
import time
import zoneinfo
from datetime import datetime
from sched import scheduler

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


# DB Stuff UwU
def init_db():
    conn = sqlite3.connect("nudgebot.db")
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS restrictlist (
        user_id TEXT PRIMARY KEY
        reason TEXT
        added_at TIMESTAMP DEFAUSLT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


init_db()


def is_user_restricted(user_id: str) -> bool:
    conn = sqlite3.connect("nudgebot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM denylist WHERE user_id =?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result is not None


def add_user_to_restrictlist(user_id: str, reason: str = ""):
    conn = sqlite3.connect("nudgebot.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR IGNORE INTO denylist (user_id, reason) VALUES (?, ?)",
        (user_id, reason),
    )
    conn.commit()
    conn.close()


# RECAP.
@app.action("open_recap_modal")
def handle_recap_button(ack, body, client, logger):
    ack()

    user_id = body["user"]["id"]

    if user_id != CMAN_USER_ID:
        client.chat_postEphemeral(
            channel=body["channel"]["id"],
            user=user_id,
            text=f"Only {CMAN_USER_ID} can only answer the recap prompt, ya goober! :neocat_knifes:",
        )
        return

    client.views_open(
        trigger_id=body["trigger_id"],
        view={
            "type": "modal",
            "callback_id": "recap_view",
            "title": {"type": "plain_text", "text": "Recap Form", "emoji": True},
            "submit": {"type": "plain_text", "text": "submit recap!", "emoji": True},
            "close": {"type": "plain_text", "text": "cancel", "emoji": True},
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "plain_text",
                        "text": f"heya, <@{user_id}>! hope you are having a nice day! mind filling this out? :neocat_aww:",
                        "emoji": True,
                    },
                },
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": "how are you feeling today?"},
                    "accessory": {
                        "type": "static_select",
                        "placeholder": {
                            "type": "plain_text",
                            "text": "Select an item",
                            "emoji": True,
                        },
                        "options": [
                            {
                                "text": {
                                    "type": "plain_text",
                                    "text": ":neocat_happy: excited!",
                                    "emoji": True,
                                },
                                "value": "value-0",
                            },
                            {
                                "text": {
                                    "type": "plain_text",
                                    "text": ":neocat: happy!",
                                    "emoji": True,
                                },
                                "value": "value-1",
                            },
                            {
                                "text": {
                                    "type": "plain_text",
                                    "text": ":neocat_blank: meh/neutral",
                                    "emoji": True,
                                },
                                "value": "value-2",
                            },
                            {
                                "text": {
                                    "type": "plain_text",
                                    "text": ":neocat_sad: sad",
                                    "emoji": True,
                                },
                                "value": "value-3",
                            },
                            {
                                "text": {
                                    "type": "plain_text",
                                    "text": ":neocat_up_sleep: tired",
                                    "emoji": True,
                                },
                                "value": "value-4",
                            },
                            {
                                "text": {
                                    "type": "plain_text",
                                    "text": ":neocat_x_x: stressed",
                                    "emoji": True,
                                },
                                "value": "value-5",
                            },
                            {
                                "text": {
                                    "type": "plain_text",
                                    "text": ":neocat_angry: angry",
                                    "emoji": True,
                                },
                                "value": "value-6",
                            },
                        ],
                        "action_id": "static_select-action",
                    },
                },
                {
                    "type": "input",
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "plain_text_input-action",
                    },
                    "label": {
                        "type": "plain_text",
                        "text": "what did you do today?",
                        "emoji": True,
                    },
                    "optional": False,
                },
            ],
        },
    )


@app.view("recap_view")
def handle_recap_submission(ack, body, client, view):
    ack()

    user_id = body["user"]["id"]

    state_values = view["state"]["values"]
    feeling = state_values["feeling_block"]["feeling_select"]["selected_option"][
        "text"
    ]["text"]
    fortoday = state_values["fortoday_block"]["fortoday_input"]["value"]

    client.chat_postMessage(
        channel=PERSONAL_CHANNEL_ID,
        text=f"recap for today from <@{user_id}>!\n*<@{user_id}> is feeling {feeling}\n*what did <@{user_id}> do today!\n{fortoday}",
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


@app.event("member_joined_channel")
def handle_member_invited_channel(body, client):
    channel = body["event"]["channel"]
    user = body["event"]["user"]

    if channel == PERSONAL_CHANNEL_ID:
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"hiya, {user}! :oi: welcome to {PERSONAL_CHANNEL_ID}! we hope you have a nice time chatting in this channel! :neocat_happy:",
                },
            },
            {"type": "divider"},
            {
                "type": "context",
                "elements": [
                    {
                        "type": "plain_text",
                        "text": ":wave1parrot::wave2parrot::wave3parrot::wave4parrot::wave5parrot::wave6parrot:",
                        "emoji": True,
                    }
                ],
            },
        ]
        client.chat_postMessage(
            channel=channel,
            blocks=blocks,
        )


# Join via Slash command
@app.command("/join-the-padded-room")
def joining_guardian(ack, respond, say, command, client):
    ack()

    user_id = command["user_id"]

    members_response = client.conversations_members(channel=PERSONAL_CHANNEL_ID)
    members = members_response["members"]

    if is_user_restricted(user_id):
        respond(
            f"sorry, but you are unable to join <#{PERSONAL_CHANNEL_ID}>. :neocat_sad: if you think this is a mistake, please DM <@{CMAN_USER_ID}>."
        )

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
                "text": f":neocat: User: {user_id}",
                "emoji": True,
            },
        },
        {
            "type": "section",
            "text": {
                "type": "plain_text",
                "text": ":tw_calendar: Date Joined:",
                "emoji": True,
            },
        },
        {
            "type": "section",
            "text": {
                "type": "plain_text",
                "text": f":identity-vault-transparent: IDV Status: {idv_result}",
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
                    "action_id": "accept_pc_action",
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
                    "action_id": "deny_pc_action",
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Restrict", "emoji": True},
                    "style": "danger",
                    "value": user_id,
                    "action_id": "restrict_user_action",
                },
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

    is_restricted = is_user_restricted(user_id)

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
    elif is_restricted:
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"sorry, but you are unable to join <#{PERSONAL_CHANNEL_ID}>. :neocat_sad: if you think this is a mistake, please DM <@{CMAN_USER_ID}>.",
                },
            }
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


# App Home Logic! Part 2!
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

    response = requests.get(str(HCA_API_URL), params={"slack_id": user_id})
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
                    "action_id": "accept_pc_action",
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
                    "action_id": "deny_pc_action",
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Restrict", "emoji": True},
                    "style": "danger",
                    "value": user_id,
                    "action_id": "restrict_user_action",
                },
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


@app.action("restrict_user_action")
def handle_restrict_user_pc(ack, body, client):
    ack()

    restricted_user_id = body["action"][0]["value"]

    add_user_to_restrictlist(
        restricted_user_id, reason="Channel Manager clicked Restrict"
    )

    client.chat_postMessage(
        channel=CMAN_USER_ID,
        text=f"Restricted <@{restricted_user_id}> sucessfully. They are not allowed to request to join <#{PERSONAL_CHANNEL_ID}>",
    )


@app.action("deny_pc_action")
def handle_deny_button(ack, body, client, logger):
    ack()

    user_id = body["actions"][0]["value"]

    client.chat_postMessage(
        channel=user_id,
        text="hi <@user_id>. your request to the padded room has been denied. if you think this is a mistake, please resend your request! :(",
    )


def schedule_recap_msg(client):
    MSG_HR = 21
    MSG_MIN = 0

    while True:
        try:
            tz = zoneinfo.ZoneInfo("America/New_York")
            now = datetime.now(tz)

            if now.hour == MSG_HR and now.minute == MSG_MIN:
                blocks = [
                    {
                        "type": "section",
                        "text": {
                            "type": "plain_text",
                            "text": f"<@{CMAN_USER_ID}>, it's 9 PM so it's time for your daily recap! :neocat_3c:",
                            "emoji": True,
                        },
                    },
                    {
                        "type": "actions",
                        "elements": [
                            {
                                "type": "button",
                                "text": {
                                    "type": "plain_text",
                                    "text": "open form!",
                                    "emoji": True,
                                },
                                "value": "answer_recap",
                                "action_id": "open_recap_modal",
                            }
                        ],
                    },
                ]
                client.chat_postMessage(
                    channel=PERSONAL_CHANNEL_ID, text="recap time!", blocks=blocks
                )

                time.sleep(61)
            else:
                time.sleep(30)
        except Exception as e:
            sentry_sdk.capture_exception(e)
            time.sleep(60)


if __name__ == "__main__":
    scheduler_thread = threading.Thread(
        target=schedule_recap_msg, args=(app.client,), daemon=True
    )
    scheduler_thread.start()

    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()
