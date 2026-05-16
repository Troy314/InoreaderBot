import os
import json
import asyncio
import discord
import feedparser
from dotenv import load_dotenv
from datetime import datetime, timezone
from urllib.parse import urlparse

load_dotenv()

DISCORD_TOKEN = os.environ["DISCORD_TOKEN"]

FEEDS = [
    {
        "rss_url": os.environ["INOREADER_RSS_URL_1"],
        "channel_id": int(os.environ["CHANNEL_ID_1"]),
    },
    {
        "rss_url": os.environ["INOREADER_RSS_URL_2"],
        "channel_id": int(os.environ["CHANNEL_ID_2"]),
    },
]

DIGEST_HOUR = 6       # 6h00 UTC
MAX_ARTICLES = 50
SEEN_FILE = "seen_articles.json"

def is_valid_url(url):
    try:
        result = urlparse(url)
        return all([result.scheme in ('http', 'https'), result.netloc])
    except Exception:
        return False

def load_seen():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE) as f:
            return set(json.load(f))
    return set()

def save_seen(seen: set):
    with open(SEEN_FILE, "w") as f:
        json.dump(list(seen), f)

def fetch_new_articles(rss_url: str, seen: set):
    feed = feedparser.parse(rss_url)
    new = []
    for entry in feed.entries:
        uid = entry.get("id") or entry.get("link")
        if uid not in seen:
            new.append(entry)
            seen.add(uid)
    return new[:MAX_ARTICLES]

def seconds_until_next_digest():
    now = datetime.now(timezone.utc)
    target = now.replace(hour=DIGEST_HOUR, minute=0, second=0, microsecond=0)
    if now >= target:
        target = target.replace(day=target.day + 1)
    delta = (target - now).total_seconds()
    return delta

intents = discord.Intents.default()
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f"✅ Logged in as {client.user}")
    client.loop.create_task(digest_loop())

async def digest_loop():
    await client.wait_until_ready()

    channels = []
    for feed_cfg in FEEDS:
        ch = client.get_channel(feed_cfg["channel_id"])
        if ch is None:
            print(f"❌ Channel {feed_cfg['channel_id']} not found!")
        else:
            print(f"✅ Feed → #{ch.name}")
            channels.append({"channel": ch, "rss_url": feed_cfg["rss_url"]})

    seen = load_seen()

    while not client.is_closed():
        wait = seconds_until_next_digest()
        print(f"⏳ Next digest in {wait/3600:.1f}h")
        await asyncio.sleep(wait)

        now_str = datetime.now(timezone.utc).strftime("%A %d %B %Y")

        for feed_cfg in channels:
            channel = feed_cfg["channel"]
            rss_url = feed_cfg["rss_url"]

            articles = fetch_new_articles(rss_url, seen)
            save_seen(seen)

            if not articles:
                await channel.send(f"📭 No new articles for {now_str}.")
                continue

            await channel.send(f"@everyone\n📰 **Morning digest — {now_str}** ({len(articles)} articles)")
            await asyncio.sleep(1)

            for entry in articles:
                title = entry.get("title", "No title")
                link = entry.get("link", "")
                source = entry.get("source", {}).get("title", "")

                embed = discord.Embed(
                    title=title,
                    url=link,
                    color=discord.Color.blurple()
                )
                if source:
                    embed.set_footer(text=source)

                await channel.send(embed=embed)
                await asyncio.sleep(0.5)

        await asyncio.sleep(60)

client.run(DISCORD_TOKEN)