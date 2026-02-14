import requests
import feedparser
import random
import datetime
from core.db_manager import DBManager


class NewsScraper:
    def __init__(self):
        self.db = DBManager()
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        # 🗓️ RELIABLE SOURCES
        self.niche_map = {
            "morning": {
                "niche": "finance",
                "sources": [
                    "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10000664",  # CNBC Finance
                    "https://www.investing.com/rss/news.rss",  # Investing.com
                    "https://feeds.marketwatch.com/marketwatch/topstories/",  # MarketWatch
                ],
            },
            "noon": {
                "niche": "tech",
                "sources": [
                    "http://feeds.feedburner.com/TechCrunch/",
                    "https://www.theverge.com/rss/index.xml",
                ],
            },
            "evening": {
                "niche": "sports",
                "sources": [
                    "https://www.espn.com/espn/rss/news",
                    "https://rss.cbssports.com/RSS/headlines/news",
                ],
            },
            "night": {
                "niche": "history",
                "sources": [
                    "https://feeds.feedburner.com/britannica-on-this-day",
                    "https://www.historynet.com/feed",
                    "https://www.ancient-origins.net/rss.xml",
                ],
            },
        }

    def get_time_slot(self):
        hour = datetime.datetime.now().hour
        if 5 <= hour < 12:
            return "morning"
        elif 12 <= hour < 17:
            return "noon"
        elif 17 <= hour < 21:
            return "evening"
        else:
            return "night"

    def fetch_rss(self, url):
        print(f"   ⏳ Connecting to: {url}...")
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            if response.status_code != 200:
                print(f"      ⚠️ Status {response.status_code}")
                return []

            feed = feedparser.parse(response.content)
            if not feed.entries:
                return []
            return feed.entries[:10]
        except Exception as e:
            print(f"      ❌ Connection Failed: {e}")
            return []

    def is_boring(self, title):
        """Filters out boring keywords."""
        boring = [
            "crossword",
            "puzzle",
            "quiz",
            "podcast",
            "review",
            "roundup",
            "subscribe",
            "market snapshot",
        ]
        return any(x in title.lower() for x in boring)

    def scrape_targeted_niche(self, forced_slot=None):
        # Use the forced slot if provided, otherwise check clock
        slot = forced_slot if forced_slot else self.get_time_slot()
        config = self.niche_map.get(slot, self.niche_map["noon"])
        niche = config["niche"]

        print(f"🕵️‍♂️ Time: {slot.upper()} | Target Niche: {niche.upper()}")

        candidates = []
        for url in config["sources"]:
            entries = self.fetch_rss(url)
            for entry in entries:
                # 🛡️ SAFETY CHECK: Ensure title exists before reading it
                if not hasattr(entry, "title") or not entry.title:
                    continue

                if self.is_boring(entry.title):
                    continue

                if not self.db.task_exists(entry.title):
                    candidates.append(
                        {
                            "title": entry.title,
                            "summary": (
                                entry.summary
                                if hasattr(entry, "summary")
                                else entry.title
                            ),
                            "niche": niche,
                        }
                    )

        if not candidates:
            print("❌ No catchy news found in any source.")
            return

        winner = random.choice(candidates[:3])
        print(f"🏆 Selected: {winner['title']}")

        self.db.add_task(
            title=winner["title"],
            content=winner["summary"],
            source=f"{niche.upper()} - RSS",
            status="pending",
            extra_data={"niche": niche},
        )
