<p style="text-align: center;">nudgebot!</p>


### What is Nudgebot?

Nudgebot is a Slack bot, written in Python, that manages your personal channels simply and easily! Although, this bot is for my own channel, I still would like to share this creation to the world so people can my bot for their own channels :)

---

## Features!
Nudgebot can do many thing to make your channel organized!


### Recaps Feature
* You can schedule a time for Nudgebot to send a recap message to your channel. Click a button, fill out the form and your recap message is shared on your channel, letting people what did you do for today!
* Alongside the recap message, Nudgebot can fetch your Hackatime stats for today and include them in the recap message, so people can know what did you code for today.

### Advertise your channel feature
* With a slash command, you can advertise your channel through out your Slack workspace! With this, you can expect more people requesting to join your channel!

### Joining/Leaving Features
* People can join your channels in many ways! From your ad, a slash command or the home tab of your bot
* Don't want unverified people to join your channel? You can toggle on a setting that disallows non-verified people to request to join your channel!
* If you don't want people to request to join for some reason, you can toggle a setting that can disallow people to request, even if they are verified or not!
* When someone joins your channel, they get greeted with a welcoming message. You can adjust this in the main.py file of this repo.
* If someone leaves your channel, Nudgebot will automaticlly remove them from the usergroup that you configured, clearing up the usergroup, making sure only active people are added to the usergroup!

### Logging Features
* Nudgebot will log for those who join, leave your channel. It can also log who join or left the user group.

### Purge Feature
* Think that your channel is cluttered with inactive people? You can use a slash command to schedule a purge. During the beginning of a channel purge, everybody in your channel to respond to a DM from Nudgebot, expecting them to respond. If they don't respond, they will get removed from the channel and usergroup by the deadline.

---
### Requirements

You'll need these to run Nudgebot.
* Python (...do i even have to say this? specifically 3.13 or higher)
* A Slack bot created
  * You can created a Slack bot easily from a manifest file in this repo. 
  * You'll need to run the script once to generate a prefix for your slash commands and then replace REPLACEWITHPREFIX with the actual prefix that the script generated.
* Sentry (Optional)

---

### Quick Start!

1. Clone this repo
```bash
    git clone https://github.com/Snowflake6413/nudgebot
    cd nudgebot
```

2. Fill out the env variables in the .env.example file

3. Install dependencies  with ``uv sync``
```bash
    uv sync
```
4. Run it!
```bash
   uv run main.py
```

---
## Usage

Use the about command to check for a list of commands! You can navigate to your app home to configure some settings there.

---
### License
This repo is covered by the MIT License. Read [LICENSE](LICENSE) to read more.
