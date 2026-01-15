import requests
import ollama
import random
from bs4 import BeautifulSoup
from core.db_manager import DBManager


class NewsScraper:
    def __init__(self):
        self.db = DBManager()
        self.model = "llama3.2:3b"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

    def task_exists(self, title):
        return self.db.collection.find_one({"title": title}) is not None

    def fetch_full_content(self, url):
        try:
            response = requests.get(url, headers=self.headers, timeout=5)
            soup = BeautifulSoup(response.content, "html.parser")
            paragraphs = soup.find_all("p")
            text = " ".join([p.get_text().strip() for p in paragraphs[:4]])
            return text[:2000]
        except:
            return ""

    def pick_viral_news(self, news_list):
        if not news_list:
            return None

        print(f"🧠 AI analyzing {len(news_list)} candidates for SAFETY and VIRALITY...")

        random.shuffle(news_list)
        candidates = news_list[:20]

        list_text = "\n".join(
            [f"{i+1}. {item['title']}" for i, item in enumerate(candidates)]
        )

        # UPGRADED PROMPT: STRICT SAFETY RULES
        prompt = f"""
        You are a YouTube Content Strategist for a family-friendly tech channel.
        Here are trending stories:
        
        {list_text}
        
        TASK: Pick the ONE story that is VIRAL but SAFE.
        
        STRICT SAFETY RULES (DO NOT PICK THESE):
        - NO Politics, Government, FBI, Police, Lawsuits.
        - NO Crimes, Arrests, Death, Tragedy.
        - NO Sexual content or Scandals.
        
        GOOD TOPICS:
        - New Gadgets (iPhones, Robots).
        - Cool Science (Space, Aliens, Energy).
        - Business Tech (Companies buying companies).
        
        Reply ONLY with the number (e.g. "5"). If none are safe, reply "0".
        """

        try:
            response = ollama.chat(
                model=self.model, messages=[{"role": "user", "content": prompt}]
            )
            choice = response["message"]["content"].strip()

            import re

            match = re.search(r"\d+", choice)
            if match:
                index = int(match.group()) - 1
                if 0 <= index < len(candidates):
                    return candidates[index]
            return candidates[0]  # Fallback (hopefully safe)
        except:
            return candidates[0]

    def scrape_top_trends(self):
        print("🔍 Scraping Tech Sources...")

        # Removed "Google Tech" because it often has political news
        # Sticking to gadget-focused sites is safer
        sources = [
            {"name": "The Verge", "url": "https://www.theverge.com/rss/index.xml"},
            {"name": "TechCrunch", "url": "https://techcrunch.com/feed/"},
            {"name": "Engadget", "url": "https://www.engadget.com/rss.xml"},
            {
                "name": "Ars Technica",
                "url": "https://feeds.arstechnica.com/arstechnica/index",
            },
        ]

        all_candidates = []

        for src in sources:
            try:
                response = requests.get(src["url"], headers=self.headers, timeout=10)
                soup = BeautifulSoup(response.content, "xml")
                items = soup.find_all("item")

                count = 0
                for item in items:
                    if count >= 6:
                        break

                    title = item.title.text.strip()
                    link = item.link.text.strip() if item.link else ""
                    if not link and item.guid:
                        link = item.guid.text.strip()

                    description = ""
                    if item.description:
                        description = BeautifulSoup(
                            item.description.text, "html.parser"
                        ).get_text()

                    # BASIC KEYWORD FILTER (Immediate Rejection)
                    risky_words = [
                        "murder",
                        "kill",
                        "dead",
                        "police",
                        "arrest",
                        "court",
                        "lawsuit",
                        "prison",
                        "fbi",
                        "cia",
                        "biden",
                        "trump",
                        "war",
                        "weapon",
                    ]
                    if any(word in title.lower() for word in risky_words):
                        continue

                    if not self.task_exists(title):
                        all_candidates.append(
                            {
                                "title": title,
                                "summary": description,
                                "content_url": link,
                                "source": src["name"],
                            }
                        )
                        count += 1
            except Exception as e:
                print(f"   ⚠️ Failed {src['name']}: {e}")

        if not all_candidates:
            print("❌ No safe stories found.")
            return

        winner = self.pick_viral_news(all_candidates)

        if winner:
            print(f"🏆 SAFE WINNER ({winner['source']}): {winner['title']}")

            print("   📄 Fetching full article...")
            full_text = self.fetch_full_content(winner["content_url"])
            final_content = full_text if full_text else winner["summary"]

            self.db.add_task(
                title=winner["title"],
                content=final_content,
                source=winner["source"],
                status="pending",
            )
            print("✅ Task added.")
