import os
import json
import asyncio
import discord
import feedparser
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.environ["DISCORD_TOKEN"]
CHANNEL_ID = int(os.environ["CHANNEL_ID"])
INOREADER_RSS_URL = os.environ["INOREADER_RSS_URL"]
FETCH_INTERVAL = 1800
MAX_ARTICLES = 5
SEEN_FILE = "seen_articles.json"

def load_seen():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE) as f:
            return set(json.load(f))
    return set()

def save_seen(seen: set):
    with open(SEEN_FILE, "w") as f:
        json.dump(list(seen), f)

def get_image(entry) -> str | None:
    # Try media:content tag
    media = entry.get("media_content", [])
    if media:
        return media[0].get("url")
    # Try enclosures (podcasts/images)
    for enc in entry.get("enclosures", []):
        if enc.get("type", "").startswith("image"):
            return enc.get("href") or enc.get("url")
    # Try media:thumbnail
    thumb = entry.get("media_thumbnail", [])
    if thumb:
        return thumb[0].get("url")
    return None

def fetch_new_articles(seen: set):
    feed = feedparser.parse(INOREADER_RSS_URL)
    new = []
    for entry in feed.entries:
        uid = entry.get("id") or entry.get("link")
        if uid not in seen:
            new.append(entry)
            seen.add(uid)
    return new[:MAX_ARTICLES]

intents = discord.Intents.default()
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f"✅ Logged in as {client.user}")
    client.loop.create_task(news_loop())

async def news_loop():
    await client.wait_until_ready()
    channel = client.get_channel(CHANNEL_ID)

    if channel is None:
        print("❌ Channel not found!")
        return

    print(f"✅ Posting to #{channel.name}")
    seen = load_seen()

    while not client.is_closed():
        try:
            new_articles = fetch_new_articles(seen)
            if new_articles:
                save_seen(seen)
                for entry in new_articles:
                    title = entry.get("title", "No title")
                    link = entry.get("link", "")
                    source = entry.get("source", {}).get("title", "")
                    image_url = get_image(entry)

                    embed = discord.Embed(
                        title=title,
                        url=link,
                        color=discord.Color.blurple()
                    )
                    if source:
                        embed.set_footer(text=source)
                    if image_url:
                        embed.set_image(url=image_url)

                    await channel.send("@everyone", embed=embed)
                    await asyncio.sleep(1)
            else:
                print("No new articles.")
        except Exception as e:
            print(f"Error: {e}")

        await asyncio.sleep(FETCH_INTERVAL)

client.run(DISCORD_TOKEN)