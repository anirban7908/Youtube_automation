import edge_tts
import os
import asyncio
from mutagen.mp3 import MP3
from core.db_manager import DBManager


class VoiceEngine:
    def __init__(self):
        self.db = DBManager()

    async def generate_audio(self):
        task = self.db.collection.find_one({"status": "scripted"})
        if not task:
            return

        folder = task.get("folder_path")
        scenes = task.get("script_data", [])

        print(f"🎙️ Generating Audio for {len(scenes)} segments...")

        updated_scenes = []

        for i, scene in enumerate(scenes):
            filename = f"voice_{i}.mp3"
            path = os.path.join(folder, filename)
            text = scene["text"]

            try:
                communicate = edge_tts.Communicate(text, "en-US-GuyNeural", rate="+0%")
                await communicate.save(path)

                # Capture exact duration of this segment
                duration = MP3(path).info.length

                # Save audio info back to the scene object
                scene["audio_path"] = path
                scene["duration"] = duration
                updated_scenes.append(scene)
                print(f"   Shape {i+1}: {duration:.1f}s -> '{text[:20]}...'")

            except Exception as e:
                print(f"   ❌ Failed scene {i}: {e}")

        # Update DB with enriched scene data (now includes audio paths)
        self.db.collection.update_one(
            {"_id": task["_id"]},
            {"$set": {"script_data": updated_scenes, "status": "voiced"}},
        )
        print("✅ Audio Generation Complete.")
