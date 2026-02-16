import os
import re
from datetime import datetime, timedelta
from pymongo import MongoClient
from dotenv import load_dotenv
import difflib  # 🟢 NEW: For fuzzy text comparison

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

    # 🟢 NEW STRATEGY: 7-DAY WINDOW + FUZZY MATCH
    def task_exists(self, new_title):
        """
        Checks if a similar video was created in the last 7 days.
        Returns True if >85% similar.
        """
        # 1. Exact Match (Fastest check)
        if self.collection.find_one({"title": new_title}):
            return True

        # 2. Time Window Filter (Optimization)
        # Only fetch tasks created in the last 7 days.
        # This keeps the list small (e.g., 20 items instead of 100,000).
        cutoff_date = datetime.utcnow() - timedelta(days=7)

        recent_tasks = self.collection.find(
            {"created_at": {"$gte": cutoff_date}}, {"title": 1}
        )

        # 3. Fuzzy Logic Check
        # Compare the new title against the small list of recent titles.
        for task in recent_tasks:
            existing_title = task.get("title", "")

            # Calculate similarity ratio (0.0 to 1.0)
            similarity = difflib.SequenceMatcher(
                None, new_title.lower(), existing_title.lower()
            ).ratio()

            # Threshold: 85% similar
            # Example: "Apple iPhone 16" vs "Apple releases iPhone 16" matches.
            if similarity > 0.85:
                print(
                    f"      🚫 Duplicate Found ({int(similarity*100)}% match): '{new_title}' ≈ '{existing_title}'"
                )
                return True

        return False

    def add_task(
        self, title, content, source="manual", status="pending", extra_data=None
    ):
        # The check happens here before insertion
        if self.task_exists(title):
            print(f"      🚫 DB: Skipping Duplicate '{title[:20]}...'")
            return

        slot = extra_data.get("niche_slot", "morning")
        source_url = extra_data.get("source_url", "https://news.google.com/")
        folder_path = self.get_video_folder(slot, title)

        task = {
            "title": title,
            "content": content,
            "source": source,
            "status": status,
            "source_url": source_url,
            "niche": extra_data.get("niche", "motivation"),
            "slot": slot,
            "folder_path": folder_path,
            "created_at": datetime.utcnow(),
        }
        self.collection.insert_one(task)
        print(f"📥 Task Added: {title}")
