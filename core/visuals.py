import os
import time
import requests
import random
import re
import ollama
from core.db_manager import DBManager
from dotenv import load_dotenv
from PIL import Image
import io

load_dotenv()


class VisualScout:
    def __init__(self):
        self.db = DBManager()
        self.unsplash_key = os.getenv("UNSPLASH_ACCESS_KEY")
        self.pexels_key = os.getenv("PEXELS_API_KEY")

    def is_valid_image(self, content):
        try:
            img = Image.open(io.BytesIO(content))
            img.verify()
            return True
        except:
            return False

    def use_stock_search(self, query, path):
        # 1. Unsplash
        if self.unsplash_key:
            try:
                url = f"https://api.unsplash.com/search/photos?query={query}&per_page=3&client_id={self.unsplash_key}"
                res = requests.get(url, timeout=5)
                if res.status_code == 200 and res.json()["results"]:
                    img_url = random.choice(res.json()["results"])["urls"]["regular"]
                    content = requests.get(img_url).content
                    if self.is_valid_image(content):
                        with open(path, "wb") as f:
                            f.write(content)
                        return True
            except:
                pass

        # 2. Pexels
        if self.pexels_key:
            try:
                url = f"https://api.pexels.com/v1/search?query={query}&per_page=3"
                res = requests.get(
                    url, headers={"Authorization": self.pexels_key}, timeout=5
                )
                if res.status_code == 200 and res.json()["photos"]:
                    img_url = random.choice(res.json()["photos"])["src"]["large2x"]
                    content = requests.get(img_url).content
                    if self.is_valid_image(content):
                        with open(path, "wb") as f:
                            f.write(content)
                        return True
            except:
                pass
        return False

    def download_visuals(self):
        task = self.db.collection.find_one({"status": "voiced"})
        if not task:
            return

        scenes = task.get("script_data", [])
        folder = task["folder_path"]
        print(f"🎬 Visual Scout: Processing {len(scenes)} scenes...")

        updated_scenes = []

        for i, scene in enumerate(scenes):
            keywords = scene.get("keywords", ["nature"])
            count = scene.get("image_count", 1)

            image_paths = []

            # Download X images for this scene
            for j in range(count):
                # Rotate through keywords if we need multiple images
                kw = keywords[j % len(keywords)]
                filename = f"scene_{i}_img_{j}.jpg"
                path = os.path.join(folder, filename)

                print(f"   🖼️ Scene {i+1} (Img {j+1}/{count}): Search '{kw}'")

                if not self.use_stock_search(kw, path):
                    # Fallback
                    print(f"      ⚠️ Failed. Using placeholder.")
                    Image.new("RGB", (1080, 1920), (10, 10, 10)).save(path)

                image_paths.append(path)

            scene["image_paths"] = image_paths
            updated_scenes.append(scene)
            time.sleep(1)

        self.db.collection.update_one(
            {"_id": task["_id"]},
            {"$set": {"script_data": updated_scenes, "status": "ready_to_assemble"}},
        )
        print("✅ Visuals Secured.")
