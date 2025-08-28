# scraper_twikit.py  (Python 3.11)
from __future__ import annotations
import json
import datetime as dt
from pathlib import Path
from typing import Any, Dict, List
from twikit import Client
import asyncio
import random

async def human_pause(lo=3.0, hi=8.0):
    s = random.uniform(lo, hi)
    print(f"⏳ human pause {s:.1f}s")
    await asyncio.sleep(s)


def _get_created_dt(t):
    import datetime as dt
    # Prefer Twikit's real datetime if present
    d = getattr(t, "created_at_datetime", None)
    if isinstance(d, dt.datetime):
        return d if d.tzinfo else d.replace(tzinfo=dt.timezone.utc)

    # Fallback: try to parse the string form
    s = getattr(t, "created_at", None)
    if not isinstance(s, str):
        return None
    s = s.strip()
    # ISO first
    try:
        return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        pass
    # Classic Twitter format: 'Sat Aug 24 01:45:49 +0000 2024'
    try:
        return dt.datetime.strptime(s, "%a %b %d %H:%M:%S %z %Y")
    except Exception:
        return None

COOKIES_FILE = "cookies.json"

KOL_HANDLES: List[str] = [
    "TAOTemplar","JosephJacks_","jaltucher","KeithSingery","SiamKidd","markjeffrey",
    "Taotreasuries","here4impact","SubnetStats","mogmachine","const_reborn","shibshib89",
    "Old_Samster","bittingthembits","badenglishtea","learnbittensor","Obsessedfan5",
]

MAX_SCAN_PER_HANDLE = 60
OUT_DIR = Path(__file__).parent

def utcnow() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)

def coerce_dt(val: Any) -> dt.datetime | None:
    """Return an aware UTC datetime if possible."""
    if isinstance(val, dt.datetime):
        return val if val.tzinfo else val.replace(tzinfo=dt.timezone.utc)
    if isinstance(val, str):
        s = val.strip()
        # try ISO first
        try:
            return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
        except Exception:
            pass
        # try the classic Twitter format: 'Sat Aug 24 01:45:49 +0000 2024'
        try:
            return dt.datetime.strptime(s, "%a %b %d %H:%M:%S %z %Y")
        except Exception:
            return None
    return None

def get_created_at_dt(t: Any) -> dt.datetime | None:
    return (
        getattr(t, "created_at_datetime", None)
        or coerce_dt(getattr(t, "created_at", None))
    )

def to_iso8601_utc(d: dt.datetime | None) -> str | None:
    if d is None:
        return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=dt.timezone.utc)
    return d.astimezone(dt.timezone.utc).isoformat()

def tweet_to_jsonl_record(t: Any) -> Dict[str, Any]:
    text = getattr(t, "full_text", None) or getattr(t, "text", "") or ""
    created_dt = get_created_at_dt(t)

    is_rt = bool(getattr(t, "is_retweet", False))
    is_reply = bool(getattr(t, "is_reply", False)) or (getattr(t, "in_reply_to_status_id", None) is not None)
    is_quote = bool(getattr(t, "is_quote", False))

    links: List[str] = []
    ents = getattr(t, "entities", None)
    if isinstance(ents, dict):
        for u in ents.get("urls", []) or []:
            href = (u.get("expanded_url") or u.get("url") or "").strip()
            if href:
                links.append(href)

    media_urls: List[str] = []
    media = getattr(t, "media", None)
    if isinstance(media, (list, tuple)):
        for m in media:
            if isinstance(m, dict):
                url = m.get("media_url_https") or m.get("media_url") or m.get("url")
            else:
                url = getattr(m, "media_url_https", None) or getattr(m, "media_url", None) or getattr(m, "url", None)
            if url:
                media_urls.append(url)

    return {
        "content": text,
        "date": to_iso8601_utc(created_dt),
        "retweetedTweet": {} if is_rt else None,
        "inReplyToTweetId": "x" if is_reply else None,
        "quotedTweet": {} if is_quote else None,
        "outlinks": links,
        "media": [{"fullUrl": u} for u in media_urls],
    }
import sys
print("PYTHON:", sys.executable)
print("SCRAPER FILE:", __file__)

async def run_once() -> int:
    client = Client(language="en-US")
    client.load_cookies(COOKIES_FILE)
    print("🍪 cookies loaded")

    since = utcnow() - dt.timedelta(hours=24)
    total_written = 0

    for handle in KOL_HANDLES:
        await human_pause(3, 8)
        try:
            user = await client.get_user_by_screen_name(handle)
            items = await client.get_user_tweets(user.id, "Tweets")

            out: List[Dict[str, Any]] = []
            scanned = 0
            for t in items:
                scanned += 1
                created = get_created_at_dt(t)
                if created and created >= since:
                    out.append(tweet_to_jsonl_record(t))
                    print(f"{handle} posted at {created}, since={since}")

                if scanned >= MAX_SCAN_PER_HANDLE:
                    break

            if out:
                path = OUT_DIR / f"{handle}.jsonl"
                with path.open("w", encoding="utf-8") as f:
                    for rec in out:
                        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                total_written += 1
                print(f"✅ {handle}: wrote {len(out)} items")
            else:
                print(f"- {handle}: nothing in last 24h")


        except Exception as e:
            print(f"❌ {handle}: scrape error: {e!r}")
        finally:
            await human_pause(4, 12)

    print(f"📦 done. wrote files for {total_written} handles")
    return 0

if __name__ == "__main__":
    import asyncio
    asyncio.run(run_once())


