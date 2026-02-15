import requests
import feedparser
import random
import datetime
import ollama
import re
from core.db_manager import DBManager


class NewsScraper:
    def __init__(self):
        self.db = DBManager()
        self.model = "llama3.2:3b"
        self.headers = {"User-Agent": "Mozilla/5.0"}

        self.niche_map = {
            "morning": {
                "niche": "motivation",
                "sources": [
                    "https://tinybuddha.com/feed/",
                    "https://dailystoic.com/feed/",
                    "https://zenhabits.net/feed/",
                    "https://www.marcandangel.com/feed/",
                    "https://www.pickthebrain.com/blog/feed/",
                ],
            },
            "noon": {
                "niche": "tech",
                "sources": [
                    "http://feeds.feedburner.com/TechCrunch/",
                    "https://www.theverge.com/rss/index.xml",
                    "https://www.wired.com/feed/rss",
                    "https://gizmodo.com/rss",
                ],
            },
            "evening": {
                "niche": "nature",
                "sources": [
                    "https://www.sciencedaily.com/rss/fossils_ruins/paleontology.xml",
                    "https://www.sciencedaily.com/rss/plants_animals/endangered_animals.xml",
                    "https://news.mongabay.com/feed/",
                    "https://www.smithsonianmag.com/rss/science-nature/",
                    "https://www.earth.com/feed/",
                    "https://phys.org/rss-feed/biology-news/ecology/",
                ],
            },
            "night": {
                "niche": "history",
                "sources": [
                    "https://www.historytoday.com/feed/rss.xml",
                    "https://www.historynet.com/feed",
                    "https://www.ancient-origins.net/rss.xml",
                    "https://www.archaeology.org/news?format=feed",
                    "http://feeds.feedburner.com/HeritageDaily",
                ],
            },
        }

    def get_time_slot(self):
        h = datetime.datetime.now().hour
        if 5 <= h < 12:
            return "morning"
        elif 12 <= h < 17:
            return "noon"
        elif 17 <= h < 21:
            return "evening"
        else:
            return "night"

    def fetch_rss(self, url):
        try:
            r = requests.get(url, headers=self.headers, timeout=10)
            if r.status_code == 200:
                return feedparser.parse(r.content).entries[
                    :10
                ]  # increased to 10 for more variety
        except:
            pass
        return []

    def scrape_targeted_niche(self, forced_slot=None):
        slot = forced_slot if forced_slot else self.get_time_slot()
        config = self.niche_map.get(slot, self.niche_map["noon"])
        niche = config["niche"]

        print(f"🕵️‍♂️ Strategy: {slot.upper()} ({niche})")

        candidates = []
        for url in config["sources"]:
            entries = self.fetch_rss(url)
            for e in entries:
                if hasattr(e, "title"):
                    # Check DB to see if we already did this one
                    if not self.db.task_exists(e.title):
                        candidates.append(
                            {
                                "title": e.title,
                                "summary": getattr(e, "summary", e.title)[:2000],
                                "niche": niche,
                            }
                        )
                    else:
                        print(f"      🚫 Skipping known: {e.title[:20]}...")

        if not candidates:
            print("❌ No new unique tasks found. Try a different slot.")
            return

        # 🟢 FORCE VARIETY: Pick Randomly from the top 5 candidates
        # (Instead of asking AI which always picks the same one)
        print(f"   🎲 Choosing randomly from {len(candidates)} stories...")
        winner = random.choice(candidates)

        if winner:
            self.db.add_task(
                winner["title"],
                winner["summary"],
                f"{niche.upper()}",
                "pending",
                {"niche": niche, "niche_slot": slot},
            )
