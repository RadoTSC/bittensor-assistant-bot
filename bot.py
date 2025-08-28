import os
import subprocess
import pathlib

import discord
from discord.ext import commands
from dotenv import load_dotenv
load_dotenv()

# --- summarizer helpers ---
from typing import List, Dict, Tuple

import aiohttp
import re

async def summarize_with_kimi(prompt: str, max_tokens: int = 400):
    url = "https://llm.chutes.ai/v1/chat/completions"
    api_token = os.getenv("CHUTES_API_TOKEN")

    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json"
    }

    body = {
        "model": "moonshotai/Kimi-K2-Instruct-75k",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.3,
        "stream": False
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=body) as response:
            result = await response.json()
            return result["choices"][0]["message"]["content"]



# --- run the X scraper once (before digest) ---
async def run_scraper_once():
    proc = await asyncio.create_subprocess_exec(SCRAPER_EXE, SCRAPER_SCRIPT)
    await proc.wait()

# ---- Investor POV wrapper for subnets ----
def build_investor_prompt(subnet_name: str, raw_text: str) -> str:
    """
    Wrap pasted subnet conversations so Kimi knows to give investor-style output.
    """
    return f"""
You are my assistant helping me as a **Bittensor miner, DTao investor, and subnet sentiment analyst**.
I am actively looking to allocate capital, manage risk, and spot opportunities. 
Your job is to give me fast, sharp, investor-grade insights from the conversation below.

Focus your summary on:
- What the miners are discussing / complaining about
- How emissions, incentives, or mechanisms are being received
- Overall sentiment & mood (fear, greed, excitement, confusion, frustration, optimism, etc.)
- Any news, announcements, timelines, or hidden alpha that could move markets
- Implications for investment, profitability, and positioning

Output format:
- Start with a **tight executive summary** (2–3 crisp sentences).
- Then give **bullet points** with key signals, risks, and opportunities.
- End with a **1-line investor take**.

Here’s the copied conversation from {subnet_name}:
\"\"\"{raw_text.strip()}\"\"\"
"""


async def summarize_subnet_with_kimi(subnet_name: str, raw_text: str, max_tokens: int) -> str:
    """
    Summarize a subnet chat with the investor POV automatically applied.
    """
    prompt = build_investor_prompt(subnet_name, raw_text)
    return await summarize_with_kimi(prompt, max_tokens=max_tokens)

# --- KOL helpers reusing the SAME investor prompt ---

def join_kol_posts(posts: List[Dict]) -> str:
    """Flatten KOL posts into a single text blob for Kimi."""
    parts: List[str] = []
    for p in posts:
        t = (p.get("text") or "").strip()
        if t:
            parts.append(t)
    # safety cap to avoid huge inputs; adjust as you like
    return "\n\n".join(parts)

async def summarize_kol_with_kimi(handle: str, posts: List[Dict], max_tokens: int = 400) -> str:
    """
    Summarize a KOL's last 24h using the SAME investor POV prompt.
    """
    raw_text = join_kol_posts(posts)
    # reuse your investor prompt; just label the source for context
    prompt = build_investor_prompt(f"@{handle} (KOL feed)", raw_text)
    return await summarize_with_kimi(prompt, max_tokens=max_tokens)

# --- daily digest at 8:00 ET ---
import datetime
from zoneinfo import ZoneInfo
from discord.ext import tasks

# --- scraper runner (uses .scrape311) ---
import asyncio, os
BASE_DIR = os.path.dirname(__file__)
SCRAPER_EXE = os.path.join(BASE_DIR, ".scrape311", "Scripts", "python.exe")
SCRAPER_SCRIPT = os.path.join(BASE_DIR, "scraper_twikit.py")


DISCORD_DIGEST_CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID", "EX_CHANNEL_ID"))
KOLS_CHANNEL_ID = int(os.getenv("KOLS_CHANNEL_ID", "EX_CHANNEL_ID"))  # output for KOL summaries
NEWS_UPDATES_CHANNEL_ID = int(os.getenv("NEWS_UPDATES_CHANNEL_ID", "0"))




@tasks.loop(time=datetime.time(hour=8, minute=0, tzinfo=ZoneInfo("America/New_York")))
async def daily_digest():
    await daily_kol_summary()  # scraper + Kimi + post to KOLS channel


# ---- intents setup ----
intents = discord.Intents.default()
intents.guilds = True
intents.message_content = True

# ---- create the bot ----
bot = commands.Bot(command_prefix="!", intents=intents)

# ---- load token ----

TOKEN = os.getenv("DISCORD_TOKEN")

# ---- any globals ----
pending_confirmations = {}


# Mapping of subnet names to their corresponding channel IDs
# Add as many channels you want for bot outputs
SUBNET_CHANNELS = {
    "bitcast-93": 1409911111111222333, #Channel_ID_EX
    "ridges-62": 1409922222222333444, #Channel_ID_EX
    "chutes-64": 1409933333333444555, #Channel_ID_EX
    "flamewire-97": 1409944444444555666, #Channel_ID_EX
    "taonado-113": 1409955555555666777, #Channel_ID_EX
    "bitsec-60": 1409966666666777888, #Channel_ID_EX
    "compute-horde-12": 1409977777777888999 #Channel_ID_EX
}

# --- KOL config (order = output order at 8:00) ---
# Add as many kols as you wish to this list also.
KOL_HANDLES = [
    "TAOTemplar", "JosephJacks_", "jaltucher", "KeithSingery", "SiamKidd", "markjeffrey",
    "Taotreasuries", "here4impact", "SubnetStats", "mogmachine", "const_reborn", "shibshib89",
    "Old_Samster", "bittingthembits", "badenglishtea", "learnbittensor", "Obsessedfan5",
]

ALLOWLIST = (
    "youtube.com", "youtu.be", "github.com", "gitlab.com", "pypi.org",
    "docs.google.com", "drive.google.com", "readthedocs.io", "bittensor.com",
    "medium.com", "substack.com", "mirror.xyz"
)



def summarize_handle_posts(handle: str, posts: List[Dict]) -> Tuple[str, List[str]]:
    """Return (one-paragraph summary, links_list)."""
    # keep originals + quote-tweets; drop replies/retweets (safer defaults)
    items = [p for p in posts if not p.get("is_reply", False) and not p.get("is_retweet", False)]
    if not items:
        return "", []

    # token cap depending on number of kol post in 24hrs
    n = len(items)
    cap = 50 if n == 1 else (115 if n <= 3 else 145)

    sentences: List[str] = []
    links_all: List[str] = []
    for p in items:
        txt = (p.get("text") or "").replace("\n", " ").strip()
        if txt:
            sentences.append(txt)
        links_all.extend(p.get("links", []))
        links_all.extend(p.get("media_urls", []))  # image/video URLs

    # single paragraph under hard word cap (links/media not counted)
    words = " ".join(sentences).split()
    paragraph = " ".join(words[:cap])

    # de-dupe + allowlist-first
    seen = set()
    safe: List[str] = []
    other: List[str] = []
    for url in links_all:
        if not url or url in seen:
            continue
        seen.add(url)
        (safe if any(dom in url.lower() for dom in ALLOWLIST) else other).append(url)

    return paragraph, (safe + other)



def build_handle_section(handle: str, paragraph: str, links: List[str]) -> str:
    # show a friendly note if the handle has no posts in the last 24h
    if not paragraph:
        return f"**@{handle}**\n(nothing in the last 24h — touch grass 😎)"
    section = f"**@{handle}**\n{paragraph}"
    if links:
        section += "\n\nLinks & Media:\n" + "\n".join(f"• {u}" for u in links)
    return section



def get_posts_24h(handle: str) -> list[dict]:
    """
    Read {handle}.jsonl from the project folder (snscrape output).
    Return ONLY originals + quote-tweets from the last 24h.
    If the file is missing or there are no items, return [].
    """
    import os, json, datetime

    path = os.path.join(os.path.dirname(__file__), f"{handle}.jsonl")
    if not os.path.exists(path):
        return []

    now_utc = datetime.datetime.now(datetime.timezone.utc)
    since = now_utc - datetime.timedelta(hours=24)

    def parse_iso(s: str):
        try:
            return datetime.datetime.fromisoformat(s.replace("Z", "+00:00"))
        except Exception:
            return None

    posts: list[dict] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                it = json.loads(line)
            except Exception:
                continue

            d = parse_iso(str(it.get("date", "")))
            if not d or d.tzinfo is None or d < since:
                continue

            # keep originals + quotes; drop replies/retweets
            if it.get("retweetedTweet") is not None:
                continue
            if it.get("inReplyToTweetId") is not None:
                continue
            is_quote = it.get("quotedTweet") is not None

            links = [u for u in (it.get("outlinks") or []) if isinstance(u, str)]
            media_urls = []
            for m in (it.get("media") or []):
                if isinstance(m, dict):
                    u = m.get("fullUrl") or m.get("thumbnailUrl") or m.get("url")
                    if u:
                        media_urls.append(u)

            posts.append({
                "text": it.get("content") or "",
                "links": links,
                "media_urls": media_urls,
                "is_reply": False,
                "is_retweet": False,
                "is_quote": is_quote,
            })

    return posts



def build_daily_sections() -> list[str]:
    sections = []
    for h in KOL_HANDLES:
        posts = get_posts_24h(h)
        paragraph, links = summarize_handle_posts(h, posts)
        block = build_handle_section(h, paragraph, links)
        if block:  # skip handles with no items
            sections.append(block)
    return sections

@bot.event
async def on_ready():
    print(f"✅ Ready: {bot.user} (id: {bot.user.id})")
    print(f"🔗 Connected guilds: {len(bot.guilds)}")
    # start the 8:00 ET daily job
    if not daily_digest.is_running():
        daily_digest.start()



    successes = 0
    failures = 0

    for subnet_name, channel_id in SUBNET_CHANNELS.items():
        try:
            channel_id = int(channel_id)
        except ValueError:
            print(f"❌ {subnet_name}: channel id is not a number -> {channel_id!r}")
            failures += 1
            continue

        channel = bot.get_channel(channel_id)

        if channel is None:
            try:
                channel = await bot.fetch_channel(channel_id)
            except discord.NotFound:
                print(f"❌ {subnet_name}: ID {channel_id} not found")
                failures += 1
                continue
            except discord.Forbidden:
                print(f"❌ {subnet_name}: forbidden to view/send")
                failures += 1
                continue
            except discord.HTTPException as e:
                print(f"❌ {subnet_name}: HTTP error while fetching ({e})")
                failures += 1
                continue

        if not hasattr(channel, "send"):
            print(f"❌ {subnet_name}: destination isn’t a text channel/thread (type={type(channel).__name__})")
            failures += 1
            continue

        try:
            ch_name = getattr(channel, "name", str(channel_id))
            print(f"✅ warmed {subnet_name} -> #{ch_name} ({channel_id})")
            successes += 1
        except Exception as e:
            print(f"⚠️ {subnet_name}: warmed but couldn’t read name ({e})")
            successes += 1

    print(f"📘 pre-warm summary: {successes} ok, {failures} failed")


@bot.command()
async def hello(ctx):
    await ctx.send("Hello! I'm alive 🚀")

async def daily_kol_summary():
    await run_scraper_once()
    channel = bot.get_channel(KOLS_CHANNEL_ID) or await bot.fetch_channel(KOLS_CHANNEL_ID)
    now_et = datetime.datetime.now(ZoneInfo("America/New_York"))
    await channel.send(
        f"☀️☕ GM TRENDSETTERS — {now_et:%a %b %d} — Time to get ahead of the curve, read below the latest Bittensor news!"
    )
    print("[kols] posting to:", KOLS_CHANNEL_ID, channel)

    for handle in KOL_HANDLES:
        posts = get_posts_24h(handle)
        if not posts:
            continue

        # collect URLs from the scraped posts (text links + media)
        urls = set()
        for p in posts:
            for u in (p.get("links") or []):
                if u: urls.add(u)
            # support both shapes: ["media_urls"] or [{"url":..., "thumbnail_url":...}]
            for u in (p.get("media_urls") or []):
                if u: urls.add(u)
            for m in (p.get("media") or []):
                u = (m or {}).get("url") or (m or {}).get("thumbnail_url")
                if u: urls.add(u)
        urls = sorted(urls)

        try:
            summary = await summarize_kol_with_kimi(handle, posts)  # Kimi summary from text
        except Exception as e:
            summary = f"(Kimi error: {e!r})"

        # post summary
        await channel.send(f"**@{handle}**\n{summary}")

        # post links/media list
        if urls:
            await channel.send("**Links & Media:**\n" + "\n".join(f"• {u}" for u in urls))


@bot.command(name="kol_now")
async def kol_now(ctx):
    await ctx.send("Running KOL summary manually...")
    await daily_kol_summary()

async def handle_news_update(message: discord.Message):
    # 1) Grab all readable text from the post (plain text + embed parts)
    parts = []
    if message.content:
        parts.append(message.content)
    for e in message.embeds or []:
        if getattr(e, "title", None): parts.append(e.title)
        if getattr(e, "description", None): parts.append(e.description)
        for f in getattr(e, "fields", []) or []:
            if getattr(f, "name", None): parts.append(f.name)
            if getattr(f, "value", None): parts.append(f.value)
    raw_text = "\n\n".join(p.strip() for p in parts if p)

    # 2) Collect every URL we can find (text, attachments, embed links/images)
    links = set()
    links.update(re.findall(r"https?://\S+", raw_text))       # URLs in text
    for a in message.attachments or []:                        # files/images
        links.add(a.url)
    for e in message.embeds or []:                             # cards/previews
        if e.url: links.add(e.url)
        if getattr(e, "image", None) and e.image.url: links.add(e.image.url)
        if getattr(e, "thumbnail", None) and e.thumbnail.url: links.add(e.thumbnail.url)

    # 3) Build a concise prompt for Kimi
    prompt = f"""
You are summarizing an official Bittensor announcement.

Return:
- **Executive summary** (1–2 sentences)
- **Key points** (bullets with any dates/versions)
- **Links & Media** (just the URLs)

Text:
\"\"\"{raw_text.strip()}\"\"\"

Links:
{chr(10).join(sorted(links))}
""".strip()

    # 4) Call Kimi and post the summary back into the same channel
    try:
        summary = await summarize_with_kimi(prompt, max_tokens=350)
    except Exception as e:
        summary = f"(Kimi error: {e!r})"

    await message.channel.send(f"🧾 **Announcement summary**\n{summary}")


@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    # AUTO-SUMMARY for news channel
    if NEWS_UPDATES_CHANNEL_ID and message.channel.id == NEWS_UPDATES_CHANNEL_ID:
        await handle_news_update(message)
        await bot.process_commands(message)
        return

    # 🔒 Only allow your user ID
    if message.author.id != MY_USER_ID=YOUR_DISCORD_USER_ID:
        await bot.process_commands(message)
        return

    # Only listen in #bittensor-curation
    if message.channel.id == YOUR_BITTENSOR-CURATION_CHANNEL_ID: 
        print(f"📥 New message in #bittensor-curation: {message.content!r}")

        import re
        # Subnet number comes ONLY from what you typed (e.g., "62" or "62-")
        m = re.match(r"^\s*(\d{2,3})(?:[\s\-\:\.])?$", (message.content or ""))
        if not m:
            await bot.process_commands(message)
            return

        subnet_number = m.group(1)

        matched_option = next((k for k in SUBNET_CHANNELS if k.endswith(f"-{subnet_number}")), None)
        if not matched_option:
            await message.channel.send(f"❌ Subnet `-{subnet_number}` not found. Try one of: {', '.join(SUBNET_CHANNELS.keys())}")
            pending_confirmations[message.author.id] = {"original": message}
            return

        # Read convo: prefer attached .txt, else raw text (minus the prefix)
        raw_text = ""
        if message.attachments:
            att = message.attachments[0]
            if att.filename.endswith(".txt"):
                raw_text = (await att.read()).decode("utf-8", errors="ignore")

        if not raw_text:
            raw_text = re.sub(r"^\s*\d{2,3}[\s\-\:\.]*", "", message.content or "", count=1).strip()

        if not raw_text:
            await message.channel.send("❌ I didn’t find any text to summarize (empty message / file).")
            return

        n_words = len(raw_text.split())
        cap = 50 if n_words <= 120 else (115 if n_words <= 400 else 145)

        try:
            summary = await summarize_subnet_with_kimi(matched_option, raw_text, cap)
        except Exception as e:
            summary = f"(Kimi error: {e!r})"

        channel_id = SUBNET_CHANNELS[matched_option]
        dest = bot.get_channel(channel_id) or await bot.fetch_channel(channel_id)
        await dest.send(f"🧾 Summary:\n{summary}")
        print(f"✅ Routed + summarized {subnet_number} → {matched_option} (max_tokens={cap})")
        return

    # Retry path (unchanged except it trusts only your replies)
    elif message.reference and message.reference.resolved:
        ref = message.reference.resolved
        if ref.author == bot.user and message.author.id in pending_confirmations:
            retry_number = (message.content or "").strip()
            if not retry_number.isdigit():
                await message.channel.send("❌ Please reply with just the subnet number (e.g. 62).")
                return

            matched_option = next((k for k in SUBNET_CHANNELS if k.endswith(f"-{retry_number}")), None)
            if not matched_option:
                await message.channel.send(f"❌ Still no match for `-{retry_number}`. Please try again.")
                return

            original_msg = pending_confirmations[message.author.id]["original"]

            raw_text = ""
            if original_msg.attachments:
                att = original_msg.attachments[0]
                if att.filename.endswith(".txt"):
                    raw_text = (await att.read()).decode("utf-8", errors="ignore")
            if not raw_text:
                raw_text = re.sub(r"^\s*\d{2,3}[\s\-\:\.]*", "", original_msg.content or "", count=1).strip()

            if not raw_text:
                await message.channel.send("❌ Original message had no usable text.")
                return

            n_words = len(raw_text.split())
            cap = 400

            try:
                summary = await summarize_subnet_with_kimi(matched_option, raw_text, cap)
            except Exception as e:
                summary = f"(Kimi error: {e!r})"

            channel_id = SUBNET_CHANNELS[matched_option]
            dest = bot.get_channel(channel_id) or await bot.fetch_channel(channel_id)
            await dest.send(f"🧾 Summary:\n{summary}")
            await message.channel.send(f"✅ Routed to `{matched_option}` with summarized output.")
            del pending_confirmations[message.author.id]
            return

    # keep commands like !hello working
    await bot.process_commands(message)

bot.run(TOKEN)
