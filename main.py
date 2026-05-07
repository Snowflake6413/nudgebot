import os
import sqlite3
import threading
import time
import zoneinfo
from datetime import datetime

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
CMAN_USER_ID = os.getenv("CMAN_USER_ID")
PERSONAL_CHANNEL_ID = os.getenv("PERSONAL_CHANNEL_ID")
PERSONAL_USERGROUP_ID = os.getenv("PERSONAL_USERGROUP_ID")

app = App(token=SLACK_BOT_TOKEN)

# Sentry so good bruh
if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        enable_logs=True,
    )


@app.error
def global_error_handler(error, body, logger):
    logger.exception(f"Unhandled error: {error}")
    logger.info(f"Request body: {body}")
    if SENTRY_DSN:
        sentry_sdk.capture_exception(error)


# DB Stuff UwU
def init_db():
    conn = sqlite3.connect("nudgebot.db")
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS restrictlist (
        user_id TEXT PRIMARY KEY,
        reason TEXT,
        added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS recap_settings (
        user_id TEXT PRIMARY KEY,
        recap_time TEXT DEFAULT '21:00'
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS joining_settings (
        key TEXT PRIMARY KEY,
        value TEXT
        )
    """)
    conn.commit()
    conn.close()


init_db()


def is_user_restricted(user_id: str) -> bool:
    conn = sqlite3.connect("nudgebot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM restrictlist WHERE user_id =?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result is not None


def add_user_to_restrictlist(user_id: str, reason: str = ""):
    conn = sqlite3.connect("nudgebot.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR IGNORE INTO restrictlist (user_id, reason) VALUES (?, ?)",
        (user_id, reason),
    )
    conn.commit()
    conn.close()


def remove_user_from_restrictlist(user_id: str):
    conn = sqlite3.connect("nudgebot.db")
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM restrictlist WHERE user_id = ?",
        (user_id,),
    )
    conn.commit()
    conn.close()


def is_joining_paused() -> bool:
    conn = sqlite3.connect("nudgebot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM joining_settings WHERE key = 'is_paused'")
    result = cursor.fetchone()
    conn.close()
    return result is not None and str(result[0]) == "1"


# RECAP.
@app.action("open_recap_modal")
def handle_recap_button(ack, body, client, logger):
    ack()

    user_id = body["user"]["id"]

    if user_id != CMAN_USER_ID:
        client.chat_postEphemeral(
            channel=body["channel"]["id"],
            user=user_id,
            text=f"Only <@{CMAN_USER_ID}> can only answer the recap prompt, ya goober! :neocat_knives:",
        )
        return

    message_ts = body["message"]["ts"]

    client.views_open(
        trigger_id=body["trigger_id"],
        view={
            "type": "modal",
            "callback_id": "recap_view",
            "private_metadata": message_ts,
            "title": {"type": "plain_text", "text": "Recap Form", "emoji": True},
            "submit": {"type": "plain_text", "text": "submit recap!", "emoji": True},
            "close": {"type": "plain_text", "text": "cancel", "emoji": True},
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"heya, <@{user_id}>! hope you are having a nice day! mind filling this out? :neocat_aww:",
                    },
                },
                {
                    "type": "section",
                    "block_id": "feeling_block",
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
                        "action_id": "feeling_select",
                    },
                },
                {
                    "type": "input",
                    "block_id": "fortoday_block",
                    "element": {
                        "type": "plain_text_input",
                        "multiline": True,
                        "action_id": "fortoday_input",
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

    thread_ts = view.get("private_metadata")

    state_values = view["state"]["values"]
    feeling = state_values["feeling_block"]["feeling_select"]["selected_option"][
        "text"
    ]["text"]
    fortoday = state_values["fortoday_block"]["fortoday_input"]["value"]

    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"<@{user_id}>'s recap for today! :yesyes:",
            },
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": ":wave1parrot::wave2parrot::wave3parrot::wave4parrot::wave5parrot::wave6parrot:",
            },
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"<@{user_id}> is feeling {feeling}",
            },
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"what did <@{user_id}> do today?"},
        },
        {"type": "section", "text": {"type": "mrkdwn", "text": f"{fortoday}"}},
    ]

    client.chat_postMessage(
        channel=PERSONAL_CHANNEL_ID,
        blocks=blocks,
        thread_ts=thread_ts,
        reply_broadcast=True,
        text=f"<@{user_id}>'s recap for today!",
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


# advertise STUFF uwu
@app.command("/advertise-channel")
def advertise_channel(command, client, ack, respond, logger):
    ack()

    invoker_user_id = command["user_id"]
    trigger_id = command["trigger_id"]
    if invoker_user_id != CMAN_USER_ID:
        respond("You are not authorized to run this command!")
        return

    try:
        client.views_open(
            trigger_id=trigger_id,
            view={
                "type": "modal",
                "callback_id": "advertise_channel_modal",
                "title": {
                    "type": "plain_text",
                    "text": "Advertise Channel",
                    "emoji": True,
                },
                "submit": {"type": "plain_text", "text": "Advertise", "emoji": True},
                "close": {"type": "plain_text", "text": "Cancel", "emoji": True},
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "plain_text",
                            "text": "Enter your advertisement message! :3cnuke:",
                            "emoji": True,
                        },
                    },
                    {
                        "type": "input",
                        "block_id": "message_input_block",
                        "element": {
                            "type": "plain_text_input",
                            "action_id": "message_input-action",
                        },
                        "label": {
                            "type": "plain_text",
                            "text": "Message",
                            "emoji": True,
                        },
                        "optional": False,
                    },
                ],
            },
        )
    except Exception as e:
        logger.exception(f"Error opening advertise-channel modal: {e}")
        respond("Something went wrong opening the modal. Please try again!")


@app.view("advertise_channel_modal")
def handle_advertise_channel_submission(ack, body, view, client):
    ack()

    user_id = body["user"]["id"]

    message_text = view["state"]["values"]["message_input_block"][
        "message_input-action"
    ]["value"]

    blocks = [
        {"type": "section", "text": {"type": "mrkdwn", "text": message_text}},
        {"type": "divider"},
        {
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": f"sent by: <@{user_id}> "}],
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"an ad to join <#{PERSONAL_CHANNEL_ID}> (<@{CMAN_USER_ID}>)",
                }
            ],
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "Join Channel!",
                        "emoji": True,
                    },
                    "value": "join_from_ad",
                    "action_id": "join_pc_button_home",
                }
            ],
        },
    ]

    client.chat_postMessage(
        channel=PERSONAL_CHANNEL_ID,  # Soon.
        blocks=blocks,
    )


# when a member joins a channel
@app.event("member_joined_channel")
def handle_member_invited_channel_and_channel_join(body, client, context, say):
    channel = body["event"]["channel"]
    new_user = body["event"]["user"]
    bot_user_id = context.get("bot_user_id")

    if is_user_restricted(new_user):
        client.conversations_kick(channel=channel, user=new_user)
        return

    if new_user == bot_user_id and channel != PERSONAL_CHANNEL_ID:
        leave_blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"hi! it seems like you invited me to a channel i am not supposed to be in! this bot is configure for <@{CMAN_USER_ID}>'s channel! :neocat_sad:",
                },
            },
            {"type": "divider"},
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "if you are looking to deploy a nudgebot for your channel, please see this <https://github.com/Snowflake6413/nudgebot|github repo!> you can deploy your nudgebot on <https://dashboard.hackclub.app|Nest> since it's free!",
                },
            },
            {
                "type": "context",
                "elements": [
                    {"type": "mrkdwn", "text": "any issues? dm <@U09PHG7RLGG>!"}
                ],
            },
        ]

        say(blocks=leave_blocks)
        client.conversations_leave(channel=channel)
        return

    if channel == PERSONAL_CHANNEL_ID:
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"yo, <@{new_user}>! :oi: welcome to <@{CMAN_USER_ID}>'s channel! we hope you have fun chatting with people in this channel!",
                },
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "welcome them :drgn_wave:",
                            "emoji": True,
                        },
                        "value": "click_me_123",
                        "action_id": "sayhello",
                    }
                ],
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


# anti spam function >:(
welcomed_users = {}


# welcome button logic!
@app.action("sayhello")
def greet_new_user(ack, say, body):
    ack()

    user_id = body["user"]["id"]
    thread_ts = body["message"]["ts"]

    if thread_ts not in welcomed_users:
        welcomed_users[thread_ts] = set()

    if user_id in welcomed_users[thread_ts]:
        return

    welcomed_users[thread_ts].add(user_id)

    say(text=f"<@{user_id}> says hello :drgn_wave:", thread_ts=thread_ts)


@app.command("/list-restricted-users")
def list_restricted_users_command(ack, respond, command):
    ack()

    invoker_user_id = command["user_id"]
    if invoker_user_id != CMAN_USER_ID:
        respond("You are not authorized to run this command. :nuhuhvro:")
        return

    conn = sqlite3.connect("nudgebot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, reason, added_at FROM restrictlist")
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        respond("No restricted users in this list.")
        return
    msg = "Restricted Users:\n"
    for user_id, reason, added_at in rows:
        msg += f"<@{user_id}> - Reason: {reason} (Added: {added_at})\n"

    respond(msg)


@app.command("/restrict-from-channel")
def restrict_user_command(ack, respond, say, command, client):
    ack()

    invoker_user_id = command["user_id"]

    if invoker_user_id != CMAN_USER_ID:
        respond("You are not authorized to run this command. :nuhuhvro:")
        return

    user_id_text = command.get("text", "").strip()
    if not user_id_text:
        respond("Please provide a user to restrict, e.g., /restrict-from-channel @user")
        return

    user_id = user_id_text.replace("<@", "").replace(">", "").split("|")[0]

    add_user_to_restrictlist(user_id, reason="Restricted via slash command")
    respond(f"Successfully restricted <@{user_id}>!")


@app.command("/unrestrict-from-channel")
def unrestrict_user_command(ack, respond, say, command, client):
    ack()

    invoker_user_id = command["user_id"]

    if invoker_user_id != CMAN_USER_ID:
        respond("You are not authorized to run this command :nuhuhvro:")
        return

    user_id_text = command.get("text", "").strip()
    if not user_id_text:
        respond("Please provide a user to restrict, e.g., /restrict-from-channel @user")
        return

    user_id = user_id_text.replace("<@", "").replace(">", "").split("|")[0]

    remove_user_from_restrictlist(user_id)
    respond(f"Sucessfully unrestricted <@{user_id}>!")


@app.command("/are-you-alive")
def bot_health_check(ack, respond, command):
    ack()
    respond("yes i am alive thank you for asking")


# Join via Slash command
# free feel to change this command to anything!
@app.command("/join-a-nice-channel")
def joining_guardian(ack, respond, say, command, client, body):
    ack()

    invoker_user_id = command["user_id"]

    members_response = client.conversations_members(channel=PERSONAL_CHANNEL_ID)
    members = members_response["members"]

    if is_user_restricted(invoker_user_id):
        respond(
            f"sorry, but you are unable to join <#{PERSONAL_CHANNEL_ID}>. :neocat_sad: if you think this is a mistake, please DM <@{CMAN_USER_ID}>."
        )
        return

    if invoker_user_id in members:
        respond(f"you are already in {PERSONAL_CHANNEL_ID}, you goober :neocat_blank:")
        return

    client.chat_postMessage(
        channel=invoker_user_id,
        text=f":mhm:, <@{invoker_user_id}>. you requested access to join the padded room. The manager of the padded room shall review your request in the next working hour :nodnod:",
    )

    response = requests.get(
        "https://auth.hackclub.com/api/external/check",
        params={"slack_id": invoker_user_id},
    )
    idv_data = response.json()
    idv_result = idv_data.get("result")
    blocks = [
        {
            "type": "section",
            "text": {
                "type": "plain_text",
                "text": f"New request to <@{CMAN_USER_ID}>'s personal channel :tm:",
                "emoji": True,
            },
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f":neocat: User: <@{invoker_user_id}>",
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
                    "value": invoker_user_id,
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
                    "value": invoker_user_id,
                    "action_id": "deny_pc_action",
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Restrict", "emoji": True},
                    "style": "danger",
                    "value": invoker_user_id,
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
    is_cm = user_id == CMAN_USER_ID
    is_restricted = is_user_restricted(user_id)

    if is_cm:
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "plain_text",
                    "text": "hi, <bleh>! :drgn_wave: what settings would you like to configure your nudgebot? ",
                    "emoji": True,
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
                            "text": ":incoming_envelope: Invitation Settings",
                            "emoji": True,
                        },
                        "value": "click_me_123",
                        "action_id": "invitation_settings_action",
                    }
                ],
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": ":thread: Auto-Thread Settings",
                            "emoji": True,
                        },
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
                        "text": {
                            "type": "plain_text",
                            "text": ":clock4: Recap Settings",
                            "emoji": True,
                        },
                        "value": "click_me_123",
                        "action_id": "recap_config_action",
                    }
                ],
            },
        ]
    elif is_member:
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
                    "text": f"hey, it looks like you haven't joined <#{PERSONAL_CHANNEL_ID}>, you wanna join that channel? :neocat_wink_blep:",
                },
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"this nudgebot and the personal channel (<#{PERSONAL_CHANNEL_ID}>) above is owned by <@{CMAN_USER_ID}>!",
                    }
                ],
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Join Channel",
                            "emoji": True,
                        },
                        "value": "click_me_123",
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


@app.action("invitation_settings_action")
def configure_invitations(ack, client, body):
    ack()

    client.view_open(
        trigger_id=body["trigger_id"],
        view={
            "type": "modal",
            "title": {"type": "plain_text", "text": "Join Settings", "emoji": True},
            "submit": {"type": "plain_text", "text": "Submit", "emoji": True},
            "close": {"type": "plain_text", "text": "Cancel", "emoji": True},
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "plain_text",
                        "text": "what would you like to configure for your invitation settings? :rac_woah:",
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
                                "text": ":stop: Pause Joining",
                                "emoji": True,
                            },
                            "value": "click_me_123",
                            "action_id": "pause_joining_action",
                        }
                    ],
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "plain_text",
                            "text": "this will stop people from trying to join your channel. regardless if they are restricted.",
                            "emoji": True,
                        }
                    ],
                },
            ],
        },
    )


# Configuring the recap:tm:
@app.action("recap_config_action")
def configure_recaps(ack, body, client):
    ack()

    client.views_open(
        trigger_id=body["trigger_id"],
        view={
            "type": "modal",
            "callback_id": "recap_config_modal",
            "title": {
                "type": "plain_text",
                "text": ":clock4: Recap Settings",
                "emoji": True,
            },
            "submit": {"type": "plain_text", "text": "Submit", "emoji": True},
            "close": {"type": "plain_text", "text": "Cancel", "emoji": True},
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "plain_text",
                        "text": "What settings would you like to change about your recaps?",
                        "emoji": True,
                    },
                },
                {
                    "type": "input",
                    "block_id": "timepicker_block",
                    "element": {
                        "type": "timepicker",
                        "initial_time": "13:37",
                        "placeholder": {
                            "type": "plain_text",
                            "text": "Select time",
                            "emoji": True,
                        },
                        "action_id": "timepicker-action",
                    },
                    "label": {
                        "type": "plain_text",
                        "text": "Time when your daily recaps should be sent:",
                        "emoji": True,
                    },
                    "optional": False,
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "plain_text",
                            "text": "By default, nudgebot sends recaps in Eastern Time (America/New_York). However, you can change this in your variables.",
                            "emoji": True,
                        }
                    ],
                },
            ],
        },
    )


# modal submission
@app.view("recap_config_modal")
def handle_recap_config_submission(ack, body, view, client):
    ack()
    user_id = body["user"]["id"]

    selected_time = view["state"]["values"]["timepicker_block"]["timepicker-action"][
        "selected_time"
    ]

    conn = sqlite3.connect("nudgebot.db")
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO recap_settings (user_id, recap_time)
        VALUES (?, ?)
        ON CONFLICT(user_id) DO UPDATE SET recap_time=excluded.recap_time
        """,
        (user_id, selected_time),
    )
    conn.commit()
    conn.close()

    client.chat_postMessage(
        channel=user_id, text=f"Sucessfully changed the recap time to {selected_time}."
    )


# App Home Logic! Part 2!
@app.action("join_pc_button_home")
# This is the same logic for joining_guardian :3
def handle_join_button_app_home(ack, respond, say, body, client):
    ack()

    user_id = body["user"]["id"]

    members_response = client.conversations_members(channel=PERSONAL_CHANNEL_ID)
    members = members_response["members"]

    if user_id in members:
        client.chat_postMessage(
            channel=user_id,
            text=f"you are already in <#{PERSONAL_CHANNEL_ID}>, you goober :neocat_blank:",
        )
        return

    client.chat_postMessage(
        channel=user_id,
        text=f":mhm:, <@{user_id}>. you requested access to join the padded room. The manager of the padded room shall review your request in the next working hour :nodnod:",
    )

    response = requests.get(
        "https://auth.hackclub.com/api/external/check", params={"slack_id": user_id}
    )
    idv_data = response.json()
    idv_result = idv_data.get("result")
    blocks = [
        {
            "type": "section",
            "text": {
                "type": "plain_text",
                "text": f"New request to <@{CMAN_USER_ID}>'s channel :tm:",
                "emoji": True,
            },
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f":neocat: User: <@{user_id}>",
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

    restricted_user_id = body["actions"][0]["value"]

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
        text=f"hi <@{user_id}>. your request to <@{CMAN_USER_ID}>'s personal channel has been denied. if you think this is a mistake, please resend your request! :(",
    )


def schedule_recap_msg(client):

    while True:
        try:
            tz = zoneinfo.ZoneInfo("America/New_York")
            now = datetime.now(tz)

            current_time_str = now.strftime("%H:%M")

            conn = sqlite3.connect("nudgebot.db")
            cursor = conn.cursor()
            cursor.execute(
                "SELECT user_id FROM recap_settings WHERE recap_time = ?",
                (current_time_str,),
            )
            rows = cursor.fetchall()
            conn.close()

            if rows:
                blocks = [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"<@{CMAN_USER_ID}>, it's {current_time_str} so it's time for your daily recap! :neocat_3c:",
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


# "Watching" feature
@app.event("subteam_updated")
def handle_usergroup_watch(event, client):
    if event.get("subteam_id") != PERSONAL_USERGROUP_ID:
        return

    for user_id in event.get("added_users", []):
        client.chat_postMessage(
            channel=CMAN_USER_ID,
            text=f"<@{user_id}> just joined the usergroup! (alexanders-kittens) :yay-67:",
        )

    for user_id in event.get("removed_users", []):
        client.chat_postMessage(
            channel=CMAN_USER_ID,
            text=f"<@{user_id}> just left the usergroup! (alexanders-kittens) :saga:",
        )


# Ack
@app.action("feeling_select")
def listen_feeling(ack):
    ack()


if __name__ == "__main__":
    scheduler_thread = threading.Thread(
        target=schedule_recap_msg, args=(app.client,), daemon=True
    )
    scheduler_thread.start()

    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()
