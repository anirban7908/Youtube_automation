import edge_tts
import os
import re
import json
from mutagen.mp3 import MP3
from core.db_manager import DBManager


class VoiceEngine:
    def __init__(self):
        self.db = DBManager()
        self.output_dir = "data/audio"
        os.makedirs(self.output_dir, exist_ok=True)

    def remove_emojis(self, text):
        # Allow alphanumeric, punctuation, and spaces. Remove everything else.
        return re.sub(r'[^\w\s,!.?\'"-]', "", text)

    def get_audio_duration(self, path):
        try:
            audio = MP3(path)
            return audio.info.length
        except:
            return 60  # safe default

    async def generate_audio(self):
        task = self.db.collection.find_one({"status": "scripted"})
        if not task:
            # print("📭 No scripted tasks found.") # Optional: reduce noise
            return

        print(f"🎙️ Speaking: {task['title']}")

        # --- FIX: Handle Dictionary vs String ---
        raw_script = task.get("script", "")

        # 1. If it's a dictionary (JSON), try to find the text inside
        if isinstance(raw_script, dict):
            # Try common keys the AI might use
            if "script" in raw_script:
                raw_script = raw_script["script"]
            elif "text" in raw_script:
                raw_script = raw_script["text"]
            elif "content" in raw_script:
                raw_script = raw_script["content"]
            else:
                # Worst case: dump it to string so it doesn't crash
                raw_script = str(raw_script)

        # 2. If it's still not a string (e.g. None), make it empty string
        if not isinstance(raw_script, str):
            raw_script = str(raw_script)

        # 3. Clean it
        clean_script = self.remove_emojis(raw_script)
        # ----------------------------------------

        if not clean_script.strip():
            print("❌ Error: Script is empty after cleaning.")
            return

        path = os.path.join(self.output_dir, f"{task['_id']}.mp3")

        try:
            communicate = edge_tts.Communicate(clean_script, "en-US-ChristopherNeural")
            await communicate.save(path)

            duration = self.get_audio_duration(path)

            self.db.collection.update_one(
                {"_id": task["_id"]},
                {
                    "$set": {
                        "audio_path": path,
                        "audio_duration": duration,
                        "status": "voiced",
                    }
                },
            )

            print(f"✅ Audio saved ({duration:.1f}s).")

        except Exception as e:
            print(f"❌ Voice Generation Failed: {e}")
