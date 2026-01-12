import edge_tts
import os
import re
from mutagen.mp3 import MP3
from core.db_manager import DBManager


class VoiceEngine:
    def __init__(self):
        self.db = DBManager()
        self.output_dir = "data/audio"
        os.makedirs(self.output_dir, exist_ok=True)

    def remove_emojis(self, text):
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
            return

        path = os.path.join(self.output_dir, f"{task['_id']}.mp3")
        print(f"🎙️ Speaking: {task['title']}")

        clean_script = self.remove_emojis(task["script"])

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
