import sys
import asyncio
import argparse
import json
import os
import datetime
from core.scraper import NewsScraper
from core.brain import ScriptGenerator
from core.voice import VoiceEngine
from core.visuals import VisualScout
from core.assembler import VideoAssembler
from core.upload_prep import UploadManager
from core.db_manager import DBManager  # 🟢 Added this to fetch video details


def run_creation_pipeline(slot_name):
    print(f"\n🎬 STARTING PRODUCTION PIPELINE: {slot_name.upper()}")

    # 1. SCRAPER
    print("---------------------------------------")
    scraper = NewsScraper()
    scraper.scrape_targeted_niche(forced_slot=slot_name)

    # 2. BRAIN (Scripting)
    print("---------------------------------------")
    brain = ScriptGenerator()
    brain.generate_script()

    # 3. VOICE (Async)
    print("---------------------------------------")
    voice = VoiceEngine()
    asyncio.run(voice.generate_audio())

    # 4. VISUALS
    print("---------------------------------------")
    visuals = VisualScout()
    visuals.download_visuals()

    # 5. ASSEMBLER
    print("---------------------------------------")
    assembler = VideoAssembler()
    assembler.assemble()

    # 6. UPLOAD PREP
    print("---------------------------------------")
    prep = UploadManager()
    prep.prepare_package()

    # 🟢 7. JSON LOGGING (New Feature)
    print("---------------------------------------")
    print("📝 Logging details to JSON...")

    db = DBManager()
    # Fetch the most recent video that was just packaged
    latest_task = db.collection.find_one(
        {"status": "completed_packaged"}, sort=[("created_at", -1)]
    )

    if latest_task:
        log_entry = {
            "video_name": latest_task.get("title"),
            "description": latest_task.get("ai_description"),
            "time_slot": slot_name,
            "generated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

        log_file = "production_log.json"

        # Read existing logs or create empty list
        if os.path.exists(log_file):
            try:
                with open(log_file, "r", encoding="utf-8") as f:
                    logs = json.load(f)
            except:
                logs = []
        else:
            logs = []

        # Append and Save
        logs.append(log_entry)
        with open(log_file, "w", encoding="utf-8") as f:
            json.dump(logs, f, indent=4)

        print(f"✅ Log saved to: {log_file}")
    else:
        print("⚠️ Could not find task to log.")

    print(f"\n✅ PRODUCTION COMPLETE for {slot_name}. Ready for Upload.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "slot", help="The time slot (morning, noon, evening, night)", default="noon"
    )
    args = parser.parse_args()

    run_creation_pipeline(args.slot)
