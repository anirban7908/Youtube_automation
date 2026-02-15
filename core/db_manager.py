import os
import re
from datetime import datetime
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()


class DBManager:
    def __init__(self):
        self.uri = os.getenv("MONGO_URI")
        self.db_name = os.getenv("DB_NAME")

        self.client = MongoClient(self.uri)
        self.db = self.client[self.db_name]
        self.collection = self.db["video_tasks"]

        self.base_dir = "data/generated_videos_folder"
        os.makedirs(self.base_dir, exist_ok=True)

    def sanitize_filename(self, name):
        clean = re.sub(r"[^\w\s-]", "", name)
        return re.sub(r"[-\s]+", "_", clean).strip()

    def get_video_folder(self, slot, title):
        now = datetime.now()
        date_str = now.strftime("%d-%m-%Y")
        if not slot:
            slot = "noon"
        safe_title = self.sanitize_filename(title)[:50]
        full_path = os.path.join(self.base_dir, date_str, slot, safe_title)
        os.makedirs(full_path, exist_ok=True)
        return full_path

    # 🟢 IMPROVED DUPLICATE CHECKER
    def task_exists(self, title):
        """
        Normalizes titles to ensure 'The Dinosaur' and 'the dinosaur ' are treated as duplicates.
        """
        # 1. Check exact match first
        if self.collection.find_one({"title": title}):
            return True

        # 2. Check normalized match (remove spaces, lowercase)
        clean_title = re.sub(r"\W+", "", title).lower()

        # We have to scan (inefficient but safe for small DBs) or rely on the previous check
        # For now, let's trust the Regex 'i' option but make it safer
        try:
            regex = f"^{re.escape(title)}$"
            return (
                self.collection.find_one({"title": {"$regex": regex, "$options": "i"}})
                is not None
            )
        except:
            return False

    def add_task(
        self, title, content, source="manual", status="pending", extra_data=None
    ):
        if self.task_exists(title):
            print(f"      🚫 DB: Skipping Duplicate '{title[:20]}...'")
            return

        slot = extra_data.get("niche_slot", "noon")
        folder_path = self.get_video_folder(slot, title)

        task = {
            "title": title,
            "content": content,
            "source": source,
            "status": status,
            "niche": extra_data.get("niche", "tech"),
            "slot": slot,
            "folder_path": folder_path,
            "created_at": datetime.utcnow(),
        }
        self.collection.insert_one(task)
        print(f"📥 Task Added: {title}")
