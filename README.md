🚀Bittensor Ai Bot

A Discord bot that automates your subnet research & gives key insights on subnet sentiment to propel
your Dtao investments!

<img width="880" height="560" alt="image" src="https://github.com/user-attachments/assets/3db3216b-82bc-4958-a5f3-9aba575e0250" />

It provides:

1. **KOL Monitoring** — scrapes relevant X (Twitter) accounts and summarizes daily activity
2. **Subnet TLDR** — summarize any subnet conversation by pasting it into a channel
3. **News Watcher** — listens for official announcements and replies with investor-ready summaries

Feature Walkthrough: [Watch the demo](https://youtu.be/BysQk5eZ8MA)

X scrapping Yt Vid     : [X scraping technique](https://www.youtube.com/watch?v=6D6fVyFQD5A&t=5s)  
Shoutout [TAOTemplar & R2](https://www.youtube.com/watch?v=0NoXj4BrKnc&lc=Ugw7qiQvb_VBQk2d6kt4AaABAg)  


---

## Table of Contents

- [Overview](#overview)
- [File Overview](#file-overview)
- [Dependencies](#dependencies)
- [Setup and Installation](#setup-and-installation)
- [Usage](#usage)

---

## Overview

Designed by & for Bittensor miners & investors who are looking for quick alpha & sentiment signals.

- Tracks KOL sentiment and posts in `#bittensor-x-kols`
- Summarizes subnet discussions with copy/paste simplicity
- Converts announcements into structured updates instantly

LLM output is powered by [Chutes.ai](https://chutes.ai), using the `Kimi-K2-Instruct` model.

---

## File Overview

| File | Description |
|------|-------------|
| `bot.py` | Main Discord logic and event handlers |
| `scraper_twikit.py` | Scrapes X content using cookies (Python 3.11 required) |
| `login_twikit.py` | Loads X cookies manually |
| `.env` | Stores your API keys and channel IDs |
| `cookies.json` | Stores session tokens used for scraping (see `.example` for format) |
| `requirements.txt` | Python dependencies |

---

## Dependencies

- Python **3.11** (required for Twikit)
- `discord.py==2.4.0`
- `python-dotenv==1.0.1`
- `aiohttp==3.10.5`
- `twikit`

---

## Setup and Installation

### 1. Clone the repository

```bash
git clone https://github.com/RadoTSC/bittensor-assistant-bot.git
cd bittensor-assistant-bot
```

### 2. Activate virtual environment

```bash
python3.11 -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Create a `.env` file

```env
DISCORD_TOKEN=your_discord_bot_token
CHUTES_API_TOKEN=your_chutes_api_key

DISCORD_CHANNEL_ID=channel_id_for_manual_input  
KOLS_CHANNEL_ID=channel_id_for_kol_summaries  
NEWS_UPDATES_CHANNEL_ID=channel_id_for_announcement_monitoring
```

### 5. Set up `cookies.json` for X scraping

Create a burner X account using [mail.com](https://mail.com).  
Then open [https://x.com](https://x.com), log in, press `F12` and extract from Cookies:

- `auth_token`
- `ct0`
- `twid`

Save them in `cookies.json` like:

```json
{
  "auth_token": "your_token_here",
  "ct0": "your_ct0_value",
  "twid": "your_twid"
}
```

Then run:

```bash
python login_twikit.py
```

You should see:

```
🍪 Cookies loaded successfully  
✅ Logged in using cookies (confirmed)
```

### 6. Run the Bot


```bash
python bot.py

🧠 Subnet TLDR

To summarize subnet discussions:

Go to the #bittensor-curation channel.

Post a message starting with the subnet number followed by a dash:

62- Validators are discussing inflation adjustments and incentives.


The bot will:

Detect the subnet (e.g., 62)

Generate a summary with an investor-focused tone

Post the TLDR to the correct channel (e.g., #ridges-62)

⚠️ Important: Make sure all relevant subnet output channels are listed in your bot.py under SUBNET_CHANNELS:

SUBNET_CHANNELS = {
  "ridges-62": 123456789012345678,
  "chutes-64": 234567890123456789,
  # ...
}

🧑‍🏫 KOL Summary

KOL summaries are posted daily at 8:00 AM ET in your configured #bittensor-x-kols channel.

To run it manually, type:

!kol_now

📰 News Auto-Summary

Any message posted in your configured #bittensor-news-updates channel will be automatically summarized.

✅ Health Check

To check if the bot is online, type:

!hello

✅ Example Output
🍪 Cookies loaded successfully  
✅ Logged in using cookies (confirmed)
