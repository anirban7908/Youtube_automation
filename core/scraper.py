import requests
from bs4 import BeautifulSoup
from core.db_manager import DBManager

class NewsScraper:
    def __init__(self):
        self.db = DBManager()
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
        }

    def scrape_hacker_news(self):
        print("🌐 Scraping Hacker News...")
        url = "https://news.ycombinator.com/"
        
        try:
            response = requests.get(url, headers=self.headers)
            # 1. Parse the HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 2. Find all news titles
            # Hacker News uses <span class="titleline"> for titles
            links = soup.find_all('span', class_='titleline')
            
            count = 0
            for item in links[:10]:  # Let's just take the top 10
                anchor = item.find('a')
                title = anchor.text
                link = anchor.get('href')
                
                # 3. Save to MongoDB
                self.db.add_task(title=title, content=link, source="HackerNews")
                count += 1
            
            print(f"✅ Successfully saved {count} news items to MongoDB.")
            
        except Exception as e:
            print(f"❌ Scraping Failed: {e}")