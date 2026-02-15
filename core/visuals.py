import os
import time
import requests
import re
import random
import logging
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont
from core.db_manager import DBManager

load_dotenv()

# Setup Logs
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    filename="logs/ai_errors.log", level=logging.ERROR, format="%(asctime)s %(message)s"
)


class VisualScout:
    def __init__(self):
        self.db = DBManager()
        self.output_dir = "data/images"
        os.makedirs(self.output_dir, exist_ok=True)

        # Load All Keys
        self.unsplash_key = os.getenv("UNSPLASH_ACCESS_KEY")
        self.pexels_key = os.getenv("PEXELS_API_KEY")
        self.hf_token = os.getenv("HUGGINGFACE_API_KEY")
        self.deepai_key = os.getenv("DEEPAI_API_KEY")

    def log_error(self, source, msg):
        print(f"      📝 Logged Error ({source}): {msg}")
        logging.error(f"[{source}] {msg}")

    def save_image(self, content, path):
        try:
            with open(path, "wb") as f:
                f.write(content)
            if os.path.getsize(path) > 2000:
                return True
        except:
            pass
        return False

    def extract_keyword(self, prompt):
        """Cleans AI prompt jargon to find a searchable keyword."""
        # Strip common prefixes
        clean = re.sub(
            r"^(Visuals|Scene|Image|Photo|A shot of)[:\s]*",
            "",
            prompt,
            flags=re.IGNORECASE,
        )
        words = re.findall(r"\w+", clean)

        # Filter junk words
        stop_words = [
            "detailed",
            "realistic",
            "lighting",
            "background",
            "showing",
            "with",
            "from",
        ]
        for w in words:
            if len(w) > 4 and w.lower() not in stop_words:
                return w
        return "abstract"

    # ---------------------------------------------------------
    # LEVEL 1: UNSPLASH (Primary - Artistic Photography)
    # ---------------------------------------------------------
    def try_unsplash(self, prompt, path):
        if not self.unsplash_key:
            return False
        keyword = self.extract_keyword(prompt)
        print(f"   📷 Attempt 1 (Unsplash): Searching '{keyword}'...")

        url = "https://api.unsplash.com/search/photos"
        params = {
            "query": keyword,
            "per_page": 5,
            "orientation": "portrait",
            "client_id": self.unsplash_key,
        }

        try:
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                results = response.json().get("results")
                if results:
                    img_url = random.choice(results)["urls"]["regular"]
                    img_data = requests.get(img_url).content
                    return self.save_image(img_data, path)
        except:
            pass
        return False

    # ---------------------------------------------------------
    # LEVEL 2: PEXELS (Secondary - Stock Photography)
    # ---------------------------------------------------------
    def try_pexels(self, prompt, path):
        if not self.pexels_key:
            return False
        keyword = self.extract_keyword(prompt)
        print(f"   📷 Attempt 2 (Pexels): Searching '{keyword}'...")

        url = f"https://api.pexels.com/v1/search?query={keyword}&per_page=5&orientation=portrait"
        headers = {"Authorization": self.pexels_key}

        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                photos = response.json().get("photos")
                if photos:
                    img_url = random.choice(photos)["src"]["large2x"]
                    img_data = requests.get(img_url).content
                    return self.save_image(img_data, path)
        except:
            pass
        return False

    # ---------------------------------------------------------
    # LEVEL 3: AI BACKUPS (Hugging Face / DeepAI)
    # ---------------------------------------------------------
    def try_ai_backups(self, prompt, path):
        # Hugging Face Check
        if self.hf_token:
            print(f"   🎨 Attempt 3 (Hugging Face)...")
            api = "https://api-inference.huggingface.co/models/runwayml/stable-diffusion-v1-5"
            try:
                res = requests.post(
                    api,
                    headers={"Authorization": f"Bearer {self.hf_token}"},
                    json={"inputs": prompt},
                    timeout=20,
                )
                if res.status_code == 200:
                    return self.save_image(res.content, path)
            except:
                pass

        # DeepAI Check
        if self.deepai_key:
            print(f"   🎨 Attempt 4 (DeepAI)...")
            try:
                r = requests.post(
                    "https://api.deepai.org/api/text2img",
                    data={"text": prompt},
                    headers={"api-key": self.deepai_key},
                    timeout=20,
                )
                if r.status_code == 200:
                    img_data = requests.get(r.json()["output_url"]).content
                    return self.save_image(img_data, path)
            except:
                pass
        return False

    def generate_visual(self, prompt, task_id, index):
        filename = f"{task_id}_scene_{index}.jpg"
        path = os.path.join(self.output_dir, filename)

        if self.try_unsplash(prompt, path):
            return path
        if self.try_pexels(prompt, path):
            return path
        if self.try_ai_backups(prompt, path):
            return path

        # Placeholder fallback
        img = Image.new("RGB", (1080, 1920), color=(20, 20, 30))
        img.save(path)
        return path

    def download_visuals(self):
        task = self.db.collection.find_one({"status": "voiced"})
        if not task:
            return
        print(f"🎬 Visual Scout: {task['title']}")
        scene_assets = []
        for i, scene in enumerate(task.get("scenes", [])):
            prompt = scene.get("image_prompt", "")
            img_path = self.generate_visual(prompt, task["_id"], i)
            scene_assets.append(
                {"scene_number": i + 1, "type": "image", "path": img_path}
            )
            time.sleep(1)
        self.db.collection.update_one(
            {"_id": task["_id"]},
            {"$set": {"visual_scenes": scene_assets, "status": "ready_to_assemble"}},
        )
        print(f"✅ Secured {len(scene_assets)} Assets.")
