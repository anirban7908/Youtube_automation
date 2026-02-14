import os
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

        print(f"✅ Connected to Database: {self.db_name}")

    # -------------------------------
    # CREATE
    # -------------------------------
    # UPDATE THIS METHOD IN YOUR db_manager.py
    def add_task(
        self, title, content, source="manual", status="pending", extra_data=None
    ):
        task = {
            "title": title,
            "content": content,
            "source": source,
            "status": status,
            "metadata": {
                "video_url": None,
                "audio_path": None,
                "visual_paths": [],
                "final_video_path": None,
            },
            # Merges niche info if provided
            **(
                {"niche": extra_data["niche"]}
                if extra_data and "niche" in extra_data
                else {}
            ),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        self.collection.insert_one(task)
        print(f"📥 Task added: {title}")

    # -------------------------------
    # READ
    # -------------------------------
    def get_pending_tasks(self):
        return list(self.collection.find({"status": "pending"}))

    def get_task_by_status(self, status):
        return self.collection.find_one({"status": status})

    # -------------------------------
    # UPDATE
    # -------------------------------
    def update_task_status(self, task_id, status, extra_updates=None):
        update_data = {
            "status": status,
            "updated_at": datetime.utcnow(),
        }

        if extra_updates:
            update_data.update(extra_updates)

        self.collection.update_one(
            {"_id": task_id},
            {"$set": update_data},
        )

        print(f"🔄 Task {task_id} → {status}")

    # -------------------------------
    # SAFETY / UTILITIES
    # -------------------------------
    def task_exists(self, title):
        return self.collection.find_one({"title": title}) is not None
