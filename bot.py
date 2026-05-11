# pip install discord.py feedparser

import discord
import feedparser
import asyncio
import json
import os

# --- Config ---
DISCORD_TOKEN = os.environ["DISCORD_TOKEN"]
CHANNEL_ID = int(os.environ["CHANNEL_ID"])
INOREADER_RSS_URL = os.environ["INOREADER_RSS_URL"]
FETCH_INTERVAL = 1800   # seconds between checks (30 min)
MAX_ARTICLES = 10        # max articles to post per check
SEEN_FILE = "seen_articles.json"

# --- Helpers ---
def load_seen():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE) as f:
            return set(json.load(f))
    return set()

def save_seen(seen: set):
    with open(SEEN_FILE, "w") as f:
        json.dump(list(seen), f)

def fetch_new_articles(seen: set):
    feed = feedparser.parse(INOREADER_RSS_URL)
    new = []
    for entry in feed.entries:
        uid = entry.get("id") or entry.get("link")
        if uid not in seen:
            new.append(entry)
            seen.add(uid)
    return new[:MAX_ARTICLES]   # cap to avoid flooding

def format_entry(entry) -> str:
    title = entry.get("title", "No title")
    link = entry.get("link", "")
    source = entry.get("source", {}).get("title", "") or entry.feed.get("title", "")
    parts = [f"**{title}**"]
    if source:
        parts.append(f"*{source}*")
    if link:
        parts.append(link)
    return "\n".join(parts)

# --- Discord bot ---
intents = discord.Intents.default()
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f"✅ Logged in as {client.user}")
    client.loop.create_task(news_loop())

async def news_loop():
    await client.wait_until_ready()
    channel = client.get_channel(CHANNEL_ID)
    seen = load_seen()

    while not client.is_closed():
        try:
            new_articles = fetch_new_articles(seen)
            if new_articles:
                save_seen(seen)
                for entry in new_articles:
                    await channel.send(format_entry(entry))
                    await asyncio.sleep(1)  # small delay between posts
            else:
                print("No new articles.")
        except Exception as e:
            print(f"Error: {e}")
        await asyncio.sleep(FETCH_INTERVAL)

client.run(DISCORD_TOKEN)
