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

        # Load Keys
        self.hf_token = os.getenv("HUGGINGFACE_API_KEY")
        self.deepai_key = os.getenv("DEEPAI_API_KEY")
        self.pexels_key = os.getenv("PEXELS_API_KEY")

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

    def generate_placeholder(self, text, task_id, index):
        filename = f"{task_id}_scene_{index}.jpg"
        path = os.path.join(self.output_dir, filename)
        img = Image.new("RGB", (1080, 1920), color=(10, 10, 20))
        d = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("arial.ttf", 60)
        except:
            font = ImageFont.load_default()
        d.text(
            (50, 800), f"SCENE {index+1}\n(Visual Unavailable)", fill="red", font=font
        )
        img.save(path)
        return path

    # ---------------------------------------------------------
    # LEVEL 1: HUGGING FACE (High Quality AI)
    # ---------------------------------------------------------
    def try_huggingface(self, prompt, path):
        if not self.hf_token:
            return False

        print(f"   🎨 Attempt 1 (Hugging Face): {prompt[:30]}...")

        # Using v1.5 for speed and reliability
        api_url = "https://router.huggingface.co/hf-inference/models/runwayml/stable-diffusion-v1-5"
        headers = {"Authorization": f"Bearer {self.hf_token}"}
        payload = {
            "inputs": f"{prompt}, realistic, 4k",
            "parameters": {"negative_prompt": "blurry, bad art"},
        }

        try:
            response = requests.post(api_url, headers=headers, json=payload, timeout=30)

            if response.status_code == 200:
                return self.save_image(response.content, path)

            # Handle Loading State (Common with free tier)
            try:
                data = response.json()
                if "estimated_time" in data:
                    wait = data["estimated_time"]
                    print(f"      ⏳ Model loading... waiting {wait:.1f}s")
                    time.sleep(wait + 2)
                    response = requests.post(
                        api_url, headers=headers, json=payload, timeout=30
                    )
                    if response.status_code == 200:
                        return self.save_image(response.content, path)
            except:
                pass

            self.log_error(
                "HuggingFace", f"Status {response.status_code} - {response.text[:50]}"
            )

        except Exception as e:
            self.log_error("HuggingFace", f"Exception: {e}")

        return False

    # ---------------------------------------------------------
    # LEVEL 2: DEEP AI (Free AI Backup)
    # ---------------------------------------------------------
    def try_deepai(self, prompt, path):
        if not self.deepai_key:
            return False

        print(f"   🎨 Attempt 2 (DeepAI): Switching strategy...")

        try:
            r = requests.post(
                "https://api.deepai.org/api/text2img",
                data={"text": prompt, "grid_size": "1"},
                headers={"api-key": self.deepai_key},
                timeout=60,
            )

            if r.status_code == 200:
                url = r.json().get("output_url")
                if url:
                    img_data = requests.get(url).content
                    return self.save_image(img_data, path)
            else:
                self.log_error("DeepAI", f"Status {r.status_code}")

        except Exception as e:
            self.log_error("DeepAI", f"Exception: {e}")

        return False

    # ---------------------------------------------------------
    # LEVEL 3: PEXELS (Guaranteed Stock Photo)
    # ---------------------------------------------------------
    def try_pexels(self, prompt, path):
        if not self.pexels_key:
            return False

        # Smart Keyword Extraction (Fixes "Search for 'Visuals'" bug)
        # We strip out AI prompt jargon to find the real subject
        clean_prompt = re.sub(
            r"^(Visuals|Scene|Image|Photo of|A shot of)[:\s]*",
            "",
            prompt,
            flags=re.IGNORECASE,
        )
        words = re.findall(r"\w+", clean_prompt)

        keyword = "technology"  # Default fallback
        for w in words:
            # Pick first meaningful noun longer than 4 chars
            if len(w) > 4 and w.lower() not in [
                "detailed",
                "realistic",
                "lighting",
                "background",
            ]:
                keyword = w
                break

        print(f"   📷 Attempt 3 (Pexels): Searching '{keyword}'...")

        url = f"https://api.pexels.com/v1/search?query={keyword}&per_page=15&orientation=portrait"
        headers = {"Authorization": self.pexels_key}

        try:
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code == 200:
                data = response.json()
                if data.get("photos"):
                    photo = random.choice(data["photos"])
                    img_data = requests.get(photo["src"]["large2x"]).content
                    return self.save_image(img_data, path)
        except:
            pass
        return False

    # ---------------------------------------------------------
    # MAIN PIPELINE
    # ---------------------------------------------------------
    def generate_visual(self, prompt, task_id, index):
        filename = f"{task_id}_scene_{index}.jpg"
        path = os.path.join(self.output_dir, filename)

        # 1. Hugging Face
        if self.try_huggingface(prompt, path):
            return path

        # 2. DeepAI
        if self.try_deepai(prompt, path):
            return path

        # 3. Pexels
        if self.try_pexels(prompt, path):
            return path

        return self.generate_placeholder(prompt, task_id, index)

    def download_visuals(self):
        task = self.db.collection.find_one({"status": "voiced"})
        if not task:
            return
        print(f"🎬 Visual Scout: {task['title']}")
        scene_assets = []
        for i, scene in enumerate(task.get("scenes", [])):
            prompt = scene.get("image_prompt", "")
            img_path = self.generate_visual(prompt, task["_id"], i)
            if img_path:
                scene_assets.append(
                    {"scene_number": i + 1, "type": "image", "path": img_path}
                )
            time.sleep(1)
        self.db.collection.update_one(
            {"_id": task["_id"]},
            {"$set": {"visual_scenes": scene_assets, "status": "ready_to_assemble"}},
        )
        print(f"✅ Secured {len(scene_assets)} Assets.")
