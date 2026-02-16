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
                "niche": "space",
                "sources": [
                    "https://www.space.com/feeds/news",
                    "https://www.sciencedaily.com/rss/space_time.xml",
                    "https://www.nasa.gov/rss/dyn/breaking_news.rss",
                    "https://universetoday.com/feed",
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

    # 🟢 NEW: AI VIRAL JUDGE
    def pick_viral_topic(self, candidates, niche):
        """
        Uses Ollama to analyze titles and pick the most click-worthy one.
        """
        # Create a numbered list for the AI to read
        titles = [f"{i}. {c['title']}" for i, c in enumerate(candidates)]
        titles_text = "\n".join(titles)

        prompt = f"""
        TASK: You are a YouTube Viral Content Strategist.
        GOAL: Pick the ONE headline from the list below that has the highest potential to go VIRAL as a YouTube Short.
        NICHE: {niche}
        
        CRITERIA:
        1. Look for shock value, curiosity gaps, or major breakthroughs.
        2. Avoid boring, generic, or corporate announcements.
        
        HEADLINES:
        {titles_text}
        
        OUTPUT FORMAT: Return ONLY the index number (integer) of the best headline. Example: 5
        """

        try:
            print(
                f"   🤖 AI Judge: Analyzing {len(candidates)} headlines for virality..."
            )
            response = ollama.chat(
                model=self.model, messages=[{"role": "user", "content": prompt}]
            )

            # Extract the number from the response (e.g., "The best is 3" -> 3)
            content = response["message"]["content"].strip()
            match = re.search(r"\d+", content)

            if match:
                index = int(match.group())
                if 0 <= index < len(candidates):
                    print(
                        f"      🏆 AI Selected: '{candidates[index]['title'][:40]}...'"
                    )
                    return candidates[index]

            print("      ⚠️ AI failed to return a valid number. Picking random.")
            return random.choice(candidates)

        except Exception as e:
            print(f"      ❌ AI Error: {e}. Fallback to random.")
            return random.choice(candidates)

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
                    # The DB Manager now handles the 7-day fuzzy check
                    if not self.db.task_exists(e.title):
                        candidates.append(
                            {
                                "title": e.title,
                                "summary": getattr(e, "summary", e.title)[:3000],
                                "link": getattr(e, "link", ""),
                                "niche": niche,
                            }
                        )

        if not candidates:
            print("❌ No new unique tasks found. Try a different slot.")
            return

        # 🟢 SMART SELECTION (AI JUDGE)
        if len(candidates) > 0:
            # print({"candidates": candidates})
            winner = self.pick_viral_topic(candidates, niche)

            if winner:
                self.db.add_task(
                    winner["title"],
                    winner["summary"],
                    f"{niche.upper()}",
                    "pending",
                    {"niche": niche, "niche_slot": slot, "source_url": winner["link"]},
                )
