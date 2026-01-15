import os
import time
import requests
import urllib.parse
import random
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont
from core.db_manager import DBManager

# Load environment variables
load_dotenv()


class VisualScout:
    def __init__(self):
        self.db = DBManager()
        self.output_dir = "data/images"
        os.makedirs(self.output_dir, exist_ok=True)

        # 1. GET THE API KEY
        self.api_key = os.getenv("POLLINATIONS_API_KEY")

        if not self.api_key:
            print("⚠️ NOTE: No POLLINATIONS_API_KEY found in .env.")
            print(
                "   You might hit rate limits. Sign up at enter.pollinations.ai for a free key."
            )
        else:
            print("✅ Pollinations API Key detected. Using authenticated access.")

    def generate_placeholder(self, text, task_id, index):
        """Final fallback: Creates a simple text image so the video finishes."""
        filename = f"{task_id}_scene_{index}.jpg"
        path = os.path.join(self.output_dir, filename)

        # Create dark background
        img = Image.new("RGB", (1024, 1024), color=(10, 10, 20))
        d = ImageDraw.Draw(img)

        try:
            font = ImageFont.truetype("arial.ttf", 40)
        except:
            font = ImageFont.load_default()

        display_text = f"SCENE {index+1}\n\n(Visual Unavailable)\n\n{text[:80]}..."
        d.text((50, 450), display_text, fill=(200, 200, 200), font=font)

        img.save(path)
        print(f"      ⚠️ Saved Placeholder: {filename}")
        return path

    def is_valid_image(self, path):
        """
        Smart Check: Detects if Pollinations sent the 'Rate Limit' pixel-art card.
        The error card has very few colors (<256). Real AI photos have thousands.
        """
        try:
            with Image.open(path) as img:
                colors = img.getcolors(maxcolors=2000)
                if colors:
                    print(f"      ⚠️ Detected 'Rate Limit' Error Card. Retrying...")
                    return False
                return True
        except Exception:
            return True

    def generate_ai_image(self, prompt, task_id, index):
        filename = f"{task_id}_scene_{index}.jpg"
        path = os.path.join(self.output_dir, filename)

        print(f"   🎨 Painting Scene {index+1}...")

        safe_prompt = urllib.parse.quote(prompt)

        # 2. ADD KEY TO URL
        auth_param = f"&key={self.api_key}" if self.api_key else ""

        # 3. HEADER (Just to be safe)
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        # RETRY LOGIC
        for attempt in range(1, 3):
            try:
                # 4. RANDOM SEED (CRITICAL FIX)
                # We generate a new seed for every single attempt.
                # This prevents the server from sending us a cached "Same Image".
                seed = random.randint(1, 10000000)

                # URL with Seed
                url = f"https://image.pollinations.ai/prompt/{safe_prompt}?width=1024&height=1024&model=flux&nologo=true&seed={seed}{auth_param}"

                # 5. INCREASED TIMEOUT
                # Flux is slow. We give it 60 seconds now.
                response = requests.get(url, headers=headers, timeout=180)

                if response.status_code == 200:
                    with open(path, "wb") as f:
                        f.write(response.content)

                    # Double check we didn't get the error card
                    if self.is_valid_image(path):
                        print(f"      ✅ Success: {filename}")
                        return path
                else:
                    print(f"      ❌ Error {response.status_code}")

            except Exception as e:
                print(f"      ❌ Connection Error: {e}")

            # If failed, wait a bit
            print(f"      ⏳ Attempt {attempt} failed. Retrying...")
            time.sleep(5)

        # Fallback
        return self.generate_placeholder(prompt, task_id, index)

    def download_visuals(self):
        task = self.db.collection.find_one({"status": "voiced"})
        if not task:
            return

        scenes = task.get("scenes", [])
        if not scenes:
            return

        print(f"🎬 Generative Artist: {task['title']}")
        scene_assets = []

        for i, scene in enumerate(scenes):
            prompt = scene.get("image_prompt", "")
            if len(prompt) < 3:
                continue

            # Generate
            img_path = self.generate_ai_image(prompt, task["_id"], i)

            if img_path:
                scene_assets.append(
                    {"scene_number": i + 1, "type": "image", "path": img_path}
                )

            # Shorter delay needed now that you are authenticated!
            time.sleep(3)

        if not scene_assets:
            print("❌ Critical: No images generated.")
            return

        self.db.collection.update_one(
            {"_id": task["_id"]},
            {"$set": {"visual_scenes": scene_assets, "status": "ready_to_assemble"}},
        )
        print(f"✅ Secured {len(scene_assets)} Assets.")
