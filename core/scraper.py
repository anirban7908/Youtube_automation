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

    def fetch_article_content(self, url):
        """Visits the link and grabs the first few paragraphs."""
        try:
            # print(f"      📄 Reading article: {url[:50]}...")
            response = requests.get(url, headers=self.headers, timeout=5)
            soup = BeautifulSoup(response.content, "html.parser")

            # Find all paragraphs
            paragraphs = soup.find_all("p")

            # Join the first 5 paragraphs (enough for a summary)
            text_content = " ".join([p.get_text().strip() for p in paragraphs[:5]])

            # Cleanup
            if len(text_content) < 100:
                return ""  # Too short, probably failed
            return text_content[:1500]  # Limit to 1500 chars to save DB space

        except Exception as e:
            # print(f"      ⚠️ Could not read article: {e}")
            return ""

    def pick_viral_news(self, news_list):
        if not news_list:
            return None

        print(f"🧠 AI analyzing {len(news_list)} candidates...")

        # Shuffle and pick top 15 to analyze
        random.shuffle(news_list)
        candidates = news_list[:15]

        list_text = "\n".join(
            [
                f"{i+1}. [{item['source']}] {item['title']}"
                for i, item in enumerate(candidates)
            ]
        )

        prompt = f"""
        You are a Viral News Editor. 
        Here are today's top stories:
        
        {list_text}
        
        Task: Pick the ONE story with the highest YouTube Shorts potential.
        Criteria: Shocking, Tech/Money related, or Mass Appeal.
        
        Reply ONLY with the number (e.g. "3").
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

            return candidates[0]

        except:
            return candidates[0]

    def scrape_top_trends(self):
        print("🔍 Scraping The Verge, Wired, TechCrunch & Google...")

        sources = [
            {"name": "The Verge", "url": "https://www.theverge.com/rss/index.xml"},
            {"name": "TechCrunch", "url": "https://techcrunch.com/feed/"},
            {"name": "Wired", "url": "https://www.wired.com/feed/rss"},
            {
                "name": "Google Tech",
                "url": "https://news.google.com/rss/headlines/section/topic/TECHNOLOGY?hl=en-US&gl=US&ceid=US:en",
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
                    if count >= 5:
                        break

                    title = item.title.text.strip()
                    link = item.link.text.strip() if item.link else ""
                    if not link and item.guid:
                        link = item.guid.text.strip()

                    if not self.task_exists(title):
                        # We do NOT fetch content yet (too slow to do for all 20).
                        # We wait until the AI picks the winner.
                        all_candidates.append(
                            {
                                "title": title,
                                "content_url": link,  # Store URL for later
                                "source": src["name"],
                            }
                        )
                        count += 1

            except Exception as e:
                print(f"   ⚠️ Failed {src['name']}: {e}")

        if not all_candidates:
            print("❌ No new stories found.")
            return

        # 3. AI Selection
        winner = self.pick_viral_news(all_candidates)

        if winner:
            print(f"🏆 WINNER ({winner['source']}): {winner['title']}")

            # NOW we fetch the rich content for the winner
            print("   📄 Fetching full article text for script generation...")
            full_text = self.fetch_article_content(winner["content_url"])

            # If scraping failed, fall back to title
            final_content = full_text if full_text else winner["title"]

            self.db.add_task(
                title=winner["title"],
                content=final_content,
                source=winner["source"],
                status="pending",
            )
            print("✅ Rich-Content Task added to DB.")
