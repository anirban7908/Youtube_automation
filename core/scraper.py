import requests
from bs4 import BeautifulSoup
from core.db_manager import DBManager


class NewsScraper:
    def __init__(self):
        self.db = DBManager()

    def task_exists(self, title):
        return self.db.collection.find_one({"title": title}) is not None

    def scrape_google_tech_news(self):
        print("🔍 Scraping Google Tech Trends...")
        url = "https://news.google.com/rss/headlines/section/topic/TECHNOLOGY?hl=en-US&gl=US&ceid=US:en"

        try:
            response = requests.get(url, timeout=10)
            # Changed to "html.parser" to be safer if lxml is missing
            soup = BeautifulSoup(response.text, "xml")
            items = soup.find_all("item")

            if not items:
                print("⚠️ No Google News items found. Falling back...")
                self.scrape_hacker_news()
                return

            for item in items:
                title = item.title.text.strip()
                link = item.link.text.strip()

                if " - " in title:
                    title = title.split(" - ")[0].strip()

                if self.task_exists(title):
                    print(f"⏭️ Skipping duplicate: {title}")
                    continue

                print(f"🔥 Trending (Google): {title}")
                self.db.add_task(
                    title=title, content=link, source="GoogleNews", status="pending"
                )
                print("✅ Task added.")
                return

            print("⚠️ No new Google Tech stories found.")

        except Exception as e:
            print(f"❌ Google Scraping Failed: {e}")
            self.scrape_hacker_news()

    def scrape_hacker_news(self):
        print("🔍 Scraping Hacker News...")
        try:
            url = "https://news.ycombinator.com/"
            response = requests.get(url, timeout=10)
            soup = BeautifulSoup(response.text, "html.parser")
            items = soup.find_all("span", class_="titleline")

            for item in items:
                anchor = item.find("a")
                title = anchor.text.strip()
                link = anchor.get("href")

                if self.task_exists(title):
                    continue

                print(f"🔥 Trending (HN): {title}")
                self.db.add_task(
                    title=title, content=link, source="HackerNews", status="pending"
                )
                print("✅ Task added.")
                return

        except Exception as e:
            print(f"❌ Hacker News Failed: {e}")
