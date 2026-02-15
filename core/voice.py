import edge_tts
import os
import math
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

        print(f"🎙️ Generating Audio ({len(scenes)} segments)...")

        updated_scenes = []
        for i, scene in enumerate(scenes):
            filename = f"voice_{i}.mp3"
            path = os.path.join(folder, filename)
            text = scene["text"]

            try:
                # 🟢 SPEED BOOST: +10% (Kept your speed preference)
                communicate = edge_tts.Communicate(text, "en-US-GuyNeural", rate="+10%")
                await communicate.save(path)

                duration = MP3(path).info.length

                # Update scene data
                scene["audio_path"] = path
                scene["duration"] = duration

                # 🟢 THE FIX: TIME-BASED CALCULATION
                # Rule: Max 4.0 seconds per image.
                # logic: ceil(duration / 4.0) ensures we never exceed 4s per image
                # but splits the time equally.
                required_images = math.ceil(duration / 4.0)
                scene["image_count"] = max(1, int(required_images))

                img_duration = duration / scene["image_count"]

                updated_scenes.append(scene)
                print(
                    f"   Seg {i+1}: {duration:.1f}s -> {scene['image_count']} images (~{img_duration:.1f}s each)"
                )

            except Exception as e:
                print(f"   ❌ Failed scene {i}: {e}")

        self.db.collection.update_one(
            {"_id": task["_id"]},
            {"$set": {"script_data": updated_scenes, "status": "voiced"}},
        )
        print("✅ Audio Generation Complete.")
