import os
import requests
import random
from dotenv import load_dotenv
from moviepy import VideoFileClip
from core.db_manager import DBManager

load_dotenv()


class VisualScout:
    def __init__(self):
        self.db = DBManager()
        self.api_key = os.getenv("PIXABAY_API_KEY")
        self.output_dir = "data/videos"
        os.makedirs(self.output_dir, exist_ok=True)

    def get_video_duration(self, path):
        try:
            with VideoFileClip(path) as clip:
                return clip.duration
        except:
            return 0

    def download_visuals(self):
        task = self.db.collection.find_one({"status": "voiced"})
        if not task:
            print("📭 No voiced tasks found.")
            return

        scenes = task.get("scenes", [])
        if not scenes:
            print("❌ No scenes found in task.")
            # Safety fallback if scenes list is totally empty
            scenes = [
                {
                    "scene_number": 1,
                    "stock_keywords": [task["title"]],
                    "visual_intent": "fallback",
                }
            ]

        print(f"🎬 Downloading visuals for {len(scenes)} scenes")

        scene_clips = []
        total_duration = 0
        target_duration = int(task.get("audio_duration", 60)) + 10

        for scene in scenes:
            # --- THE FIX: Handle 'Bad' Data Types ---
            if isinstance(scene, str):
                # If scene is just a string (e.g. "Scene 1"), convert it to a dict
                scene = {
                    "scene_number": 1,
                    "stock_keywords": [scene],  # Treat the string as a keyword
                    "visual_intent": "fallback",
                }
            # ----------------------------------------

            scene_id = scene.get("scene_number", "unknown")
            keywords = scene.get("stock_keywords", [])

            # Handle string keywords vs list keywords
            if isinstance(keywords, str):
                keywords = [k.strip() for k in keywords.split(",")]

            # Use title as backup keyword if empty
            if not keywords:
                keywords = ["technology abstract", "news background"]

            print(f"🔍 Scene {scene_id}: {keywords}")

            clips_for_scene = []

            # Limit to checking top 2 keywords to save time/requests
            for term in keywords[:2]:
                url = f"https://pixabay.com/api/videos/?key={self.api_key}&q={term}&per_page=5"

                try:
                    res = requests.get(url).json()
                    hits = res.get("hits", [])

                    if not hits:
                        continue

                    video_data = random.choice(hits)
                    v_url = video_data["videos"]["medium"]["url"]

                    filename = (
                        f"{task['_id']}_scene{scene_id}_{random.randint(100,999)}.mp4"
                    )
                    path = os.path.join(self.output_dir, filename)

                    with requests.get(v_url, stream=True) as r:
                        with open(path, "wb") as f:
                            for chunk in r.iter_content(1024 * 1024):
                                f.write(chunk)

                    duration = self.get_video_duration(path)
                    total_duration += duration

                    clips_for_scene.append(
                        {"scene": scene_id, "path": path, "duration": duration}
                    )
                    print(f"   ⬇️ {term} ({duration:.1f}s)")

                except Exception as e:
                    print(f"   ⚠️ Error for '{term}': {e}")

            if clips_for_scene:
                scene_clips.append({"scene_number": scene_id, "clips": clips_for_scene})

        print(f"⏱️ Footage secured: {total_duration:.1f}s")

        # Fallback if still short
        fallback_terms = [
            "abstract technology",
            "digital network",
            "futuristic city",
            "data visualization",
        ]

        while total_duration < target_duration:
            term = random.choice(fallback_terms)
            print(f"➕ Adding fallback: {term}")

            url = f"https://pixabay.com/api/videos/?key={self.api_key}&q={term}&per_page=5"
            try:
                res = requests.get(url).json()
                hits = res.get("hits", [])
                if not hits:
                    break

                video_data = random.choice(hits)
                v_url = video_data["videos"]["medium"]["url"]

                filename = f"{task['_id']}_fallback_{random.randint(1000,9999)}.mp4"
                path = os.path.join(self.output_dir, filename)

                with requests.get(v_url, stream=True) as r:
                    with open(path, "wb") as f:
                        for chunk in r.iter_content(1024 * 1024):
                            f.write(chunk)

                duration = self.get_video_duration(path)
                total_duration += duration

                scene_clips.append(
                    {
                        "scene_number": "fallback",
                        "clips": [{"path": path, "duration": duration}],
                    }
                )
            except:
                break

        self.db.collection.update_one(
            {"_id": task["_id"]},
            {"$set": {"visual_scenes": scene_clips, "status": "ready_to_assemble"}},
        )

        print(f"✅ Visuals ready for assembly ({total_duration:.1f}s)")
