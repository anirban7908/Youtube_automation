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
        self.pexels_key = os.getenv("PEXELS_API_KEY")
        self.pixabay_key = os.getenv("PIXABAY_API_KEY")
        self.output_dir = "data/videos"
        os.makedirs(self.output_dir, exist_ok=True)

    def get_video_duration(self, path):
        try:
            with VideoFileClip(path) as clip:
                return clip.duration
        except:
            return 0

    def search_pexels(self, query):
        """Search Pexels API"""
        if not self.pexels_key:
            return []

        headers = {"Authorization": self.pexels_key}
        url = f"https://api.pexels.com/videos/search?query={query}&orientation=portrait&per_page=5"
        try:
            res = requests.get(url, headers=headers, timeout=5).json()
            return [
                v["video_files"][0]["link"]
                for v in res.get("videos", [])
                if v.get("video_files")
            ]
        except Exception as e:
            print(f"   ⚠️ Pexels error: {e}")
            return []

    def search_pixabay(self, query):
        """Search Pixabay API"""
        if not self.pixabay_key:
            return []

        url = f"https://pixabay.com/api/videos/?key={self.pixabay_key}&q={query}&per_page=5"
        try:
            res = requests.get(url, timeout=5).json()
            return [v["videos"]["medium"]["url"] for v in res.get("hits", [])]
        except Exception as e:
            print(f"   ⚠️ Pixabay error: {e}")
            return []

    def download_visuals(self):
        task = self.db.collection.find_one({"status": "voiced"})
        if not task:
            print("📭 No voiced tasks found.")
            return

        scenes = task.get("scenes", [])
        if not scenes:
            print("❌ No scenes found.")
            scenes = [
                {
                    "scene_number": 1,
                    "stock_keywords": [task["title"]],
                    "visual_intent": "fallback",
                }
            ]

        print(f"🎬 Hybrid Visual Scout: {task['title']}")

        scene_clips = []
        total_duration = 0
        target_duration = int(task.get("audio_duration", 60)) + 5

        for scene in scenes:
            # Handle string data fix
            if isinstance(scene, str):
                scene = {
                    "scene_number": 1,
                    "stock_keywords": [scene],
                    "visual_intent": "fallback",
                }

            scene_id = scene.get("scene_number", "unknown")
            keywords = scene.get("stock_keywords", [])

            # Ensure keywords is a list
            if isinstance(keywords, str):
                keywords = [k.strip() for k in keywords.split(",")]
            if not keywords:
                keywords = ["technology background"]

            print(f"🔍 Scene {scene_id}: {keywords}")

            clips_for_scene = []

            for term in keywords[:2]:
                # --- STRATEGY: Try Pexels First, Then Pixabay ---
                video_urls = self.search_pexels(term)

                # If Pexels fails or returns nothing, try Pixabay
                if not video_urls:
                    # print(f"   Shape-shift: Pexels empty for '{term}', trying Pixabay...")
                    video_urls = self.search_pixabay(term)

                if not video_urls:
                    print(f"   ❌ No videos found for '{term}' on either platform.")
                    continue

                # Download random video from results
                v_url = random.choice(video_urls)
                filename = (
                    f"{task['_id']}_scene{scene_id}_{random.randint(100,999)}.mp4"
                )
                path = os.path.join(self.output_dir, filename)

                try:
                    with requests.get(v_url, stream=True) as r:
                        with open(path, "wb") as f:
                            for chunk in r.iter_content(1024 * 1024):
                                f.write(chunk)

                    duration = self.get_video_duration(path)
                    total_duration += duration
                    clips_for_scene.append(
                        {"scene": scene_id, "path": path, "duration": duration}
                    )
                    print(f"   ⬇️ Secured clip ({duration:.1f}s)")
                except Exception as e:
                    print(f"   ⚠️ Download failed: {e}")

            if clips_for_scene:
                scene_clips.append({"scene_number": scene_id, "clips": clips_for_scene})

        # --- FALLBACK LOOP ---
        fallback_terms = [
            "abstract loop",
            "news background",
            "digital connection",
            "blue futuristic",
        ]
        while total_duration < target_duration:
            term = random.choice(fallback_terms)
            print(f"➕ Adding fallback: {term}")

            # Try Pixabay for fallbacks (usually better for loops)
            urls = self.search_pixabay(term)
            if not urls:
                urls = self.search_pexels(term)

            if urls:
                v_url = random.choice(urls)
                path = os.path.join(
                    self.output_dir,
                    f"{task['_id']}_fallback_{random.randint(1000,9999)}.mp4",
                )
                try:
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
                    pass
            else:
                break  # Avoid infinite loop if internet is down

        self.db.collection.update_one(
            {"_id": task["_id"]},
            {"$set": {"visual_scenes": scene_clips, "status": "ready_to_assemble"}},
        )
        print(f"✅ Visuals ready ({total_duration:.1f}s)")
