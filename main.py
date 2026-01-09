from core.scraper import NewsScraper

def main():
    # Initialize the Scraper
    scraper = NewsScraper()
    
    # Run the news collection
    scraper.scrape_hacker_news()

if __name__ == "__main__":
    main()