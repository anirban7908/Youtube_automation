from bson import ObjectId
from core.db_manager import DBManager


def fix_broken_task():
    db = DBManager()

    # This is the ID from the record you shared
    target_id = ObjectId("69649471de6c2be2cd7eb523")

    print(f"🔧 Attempting to fix task: {target_id}")

    # 1. Clean Script (Removed "Hook", "Shopper:", and visual instructions)
    clean_script = (
        "I just saw something that made me question the entire retail system. "
        "As I was shopping at this local Goodwill, I noticed something strange. "
        "Most of the items were from 2019... and some were even older! "
        "But here's the thing: most people don't realize that expired or 'near-expired' items "
        "can still be sold as new. It's like, what even is normal? "
        "So, I'm calling on all of you to be more informed shoppers! "
        "Share your own experiences in the comments below and let's start a movement. "
        "Are we truly seeing what we think we're seeing?"
    )

    # 2. Correct Scene Format (List of Dictionaries, NOT strings)
    # This fixes the "AttributeError: 'str' object has no attribute 'get'"
    new_scenes = [
        {
            "scene_number": 1,
            "stock_keywords": ["shocked person face", "confused shopper"],
            "visual_intent": "Hook reaction",
        },
        {
            "scene_number": 2,
            "stock_keywords": ["empty store shelves", "grocery aisle"],
            "visual_intent": "The problem",
        },
        {
            "scene_number": 3,
            "stock_keywords": ["expired food label", "calendar date"],
            "visual_intent": "Detail shot",
        },
        {
            "scene_number": 4,
            "stock_keywords": ["garbage bin", "waste management"],
            "visual_intent": "Context",
        },
        {
            "scene_number": 5,
            "stock_keywords": ["question mark", "person thinking"],
            "visual_intent": "CTA",
        },
    ]

    # 3. Update Database
    result = db.collection.update_one(
        {"_id": target_id},
        {
            "$set": {
                "script": clean_script,
                "scenes": new_scenes,
                # Reset status to 'scripted' so VoiceEngine picks it up
                "status": "scripted",
                # Clear old broken paths to force regeneration
                "audio_path": None,
                "visual_scenes": [],
                "final_video_path": None,
            }
        },
    )

    if result.modified_count > 0:
        print("✅ Success! Task repaired.")
        print("🚀 You can now run 'python main.py' to generate the video.")
    else:
        print("❌ Task not found. Double check the ID in MongoDB Compass.")


if __name__ == "__main__":
    fix_broken_task()
