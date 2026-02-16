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

    # 🟢 NEW: Google Image Scraper for specific Main Topics
    def search_google_images(self, query, path):
        print(f"      🌍 Web Search: hunting for '{query}'...")
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36"
        }

        try:
            # 1. Search Google Images
            url = f"https://www.google.com/search?q={query}&tbm=isch&udm=2"  # udm=2 forces new image layout
            res = requests.get(url, headers=headers, timeout=10)

            # 2. Extract first valid image URL using Regex (looks for http...jpg/png inside script tags)
            # This pattern finds the large original images in Google's data blobs
            matches = re.findall(r'"(https?://[^"]+?\.(?:jpg|jpeg|png))"', res.text)

            if matches:
                # Try the first 3 matches (sometimes the first is a logo or icon)
                for img_url in matches[:3]:
                    try:
                        # Decrypt unicode (e.g. \u003d -> =)
                        img_url = img_url.encode().decode("unicode_escape")

                        # Download
                        img_data = requests.get(
                            img_url, headers=headers, timeout=5
                        ).content
                        if self.is_valid_image(img_data):
                            with open(path, "wb") as f:
                                f.write(img_data)
                            print("      ✅ Web Image Secured.")
                            return True
                    except:
                        continue
        except Exception as e:
            print(f"      ❌ Web Search Failed: {e}")

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

            for j in range(count):
                kw = keywords[j % len(keywords)]
                filename = f"scene_{i}_img_{j}.jpg"
                path = os.path.join(folder, filename)

                print(f"   🖼️ Scene {i+1} (Img {j+1}/{count}): Search '{kw}'")

                success = False

                # 🟢 LOGIC UPDATE: Force Web Search for the HERO IMAGE (Scene 0, Image 0)
                # This ensures the "Main Topic" (e.g. Moflin) is shown first.
                if i == 0 and j == 0:
                    success = self.search_google_images(kw, path)

                # If Web search wasn't used or failed, try Stock sites
                if not success:
                    success = self.use_stock_search(kw, path)

                # 🟢 FALLBACK: If specific keyword fails, try others in the list
                if not success:
                    for fallback_kw in keywords:
                        if fallback_kw != kw:
                            print(
                                f"      ⚠️ '{kw}' failed. Retrying with '{fallback_kw}'..."
                            )
                            if self.use_stock_search(fallback_kw, path):
                                success = True
                                break

                # Final Fallback: Placeholder
                if not success:
                    print(f"      ❌ All searches failed. Using placeholder.")
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
