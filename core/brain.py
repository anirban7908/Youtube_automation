import json
import re
import ollama
from core.db_manager import DBManager


class ScriptGenerator:
    def __init__(self):
        self.db = DBManager()
        self.model = "llama3.2:3b"

    def repair_json(self, json_str):
        try:
            # Clean generic AI chatter
            json_str = re.sub(r"^[^{]*", "", json_str)
            json_str = re.sub(r"[^}]*$", "", json_str)
            return json.loads(json_str)
        except:
            return None

    def generate_script(self):
        task = self.db.collection.find_one({"status": "pending"})
        if not task:
            print("📭 No pending tasks.")
            return

        niche = task.get("niche", "tech")
        source = task.get("content", "")[:3000]

        prompt = f"""
        ROLE: Documentary Director.
        TASK: Convert this news into a structured video script.
        SOURCE: "{source}"
        
        REQUIREMENTS:
        1. Break the story into 6-8 distinct SCENES.
        2. 'text': The narration for that scene (1-2 sentences).
        3. 'keywords': The BEST search terms for stock photos (list of 2 strings).
        4. 'image_count': Should this scene have 1 image (slow) or 2 images (fast)? (Integer).
        5. **CRITICAL**: The FINAL SCENE must end with a Call to Action (e.g., "Follow for more {niche} news", "Like and Subscribe for updates").
        
        OUTPUT FORMAT (JSON ONLY):
        {{
            "title": "Viral Title",
            "scenes": [
                {{
                    "text": "Scientists have made a shocking discovery.",
                    "keywords": ["Scientist", "Lab"],
                    "image_count": 1
                }},
                {{
                    "text": "Like and subscribe for more daily discoveries!",
                    "keywords": ["Thumbs up", "Community"],
                    "image_count": 1
                }}
            ]
        }}
        """

        try:
            print(f"🧠 AI Director: Segmenting {niche.upper()} story...")
            response = ollama.chat(
                model=self.model,
                format="json",
                messages=[{"role": "user", "content": prompt}],
            )

            data = self.repair_json(response["message"]["content"])
            if not data or "scenes" not in data:
                raise ValueError("Invalid JSON structure from AI")

            self.db.collection.update_one(
                {"_id": task["_id"]},
                {
                    "$set": {
                        "script_data": data["scenes"],
                        "title": data.get("title", task["title"]),
                        "status": "scripted",
                    }
                },
            )
            print(f"✅ Script Segmented: {len(data['scenes'])} scenes created.")

        except Exception as e:
            print(f"❌ Brain Error: {e}")
