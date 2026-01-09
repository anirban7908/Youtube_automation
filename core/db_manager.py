import os
from pymongo import MongoClient
from dotenv import load_dotenv

# Load variables from .env
load_dotenv()

class DBManager:
    def __init__(self):
        # Get settings from environment variables
        self.uri = os.getenv("MONGO_URI")
        self.db_name = os.getenv("DB_NAME")
        
        # Initialize Client
        self.client = MongoClient(self.uri)
        self.db = self.client[self.db_name]
        self.collection = self.db["video_tasks"]
        print(f"✅ Connected to Database: {self.db_name}")

    def add_task(self, title, content, source="manual"):
        """Inserts a new news/video task into MongoDB"""
        task = {
            "title": title,
            "content": content,
            "source": source,
            "status": "pending",  # Statuses: pending, processing, completed, failed
            "metadata": {
                "created_at": None, # We can add timestamps later
                "video_url": None
            }
        }
        return self.collection.insert_one(task)

    def get_pending_tasks(self):
        """Returns all tasks that are ready to be turned into videos"""
        return list(self.collection.find({"status": "pending"}))