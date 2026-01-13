import re
import ollama
from core.db_manager import DBManager


class ScriptGenerator:
    def __init__(self):
        self.db = DBManager()
        self.model = "llama3.2:3b"

    def check_ollama(self):
        try:
            ollama.list()
            return True
        except:
            print("❌ ERROR: Ollama is not running!")
            return False

    def clean_script_text(self, text):
        # Remove intros/outros
        text = re.sub(r"^(Here is|Here's|Sure).+?:", "", text, flags=re.IGNORECASE)
        # Remove visual directions
        text = re.sub(r"[\(\[].*?[\)\]]", "", text)
        # Remove labels
        text = re.sub(r"^(Hook|Scene \d+|Narrator):", "", text, flags=re.MULTILINE)
        return "\n".join([line.strip() for line in text.splitlines() if line.strip()])

    def clean_keyword(self, text):
        text = re.sub(r"^\d+[\.\)\-\s]+", "", text)
        text = re.sub(
            r"\b(visuals|eg|related to|stock footage)\b", "", text, flags=re.IGNORECASE
        )
        text = re.sub(r"[^\w\s]", "", text)
        words = text.split()
        if len(words) > 3:
            text = " ".join(words[:3])
        return text.strip()

    def generate_script(self):
        if not self.check_ollama():
            return

        task = self.db.collection.find_one({"status": "pending"})
        if not task:
            print("📭 No pending tasks.")
            return

        print(f"🧠 AI generating script for: {task['title']}")

        # ---------------- STEP 1: SCRIPT (CONTENT AWARE) ----------------
        # We now feed the Scraped Article Content into the prompt
        script_prompt = f"""
        You are a YouTube Shorts Scriptwriter.
        
        NEWS SOURCE DATA:
        "{task.get('content', '')}"
        
        TASK:
        Write a viral script summarizing this news.
        
        STRICT CONSTRAINTS:
        1. Total Length: 80 to 110 words MAX. (Target: 40-45 seconds).
        2. Do NOT use the phrase "Welcome back" or "Hey guys". Start with the news.
        3. Spoken words ONLY. No visual instructions.
        4. Tone: Urgent, Exciting.
        """

        try:
            res_script = ollama.chat(
                model=self.model, messages=[{"role": "user", "content": script_prompt}]
            )
            clean_script = self.clean_script_text(
                res_script["message"]["content"].strip()
            )

            if not clean_script:
                return

            # ---------------- STEP 2: SCENES ----------------
            scene_prompt = f"""
            Script: "{clean_script}"
            
            Task: List 5 to 7 GENERIC stock video search terms.
            Constraint: Do NOT use specific names (e.g., use "smartphone" not "iPhone 15").
            
            Output 1 keyword per line.
            """

            res_scenes = ollama.chat(
                model=self.model, messages=[{"role": "user", "content": scene_prompt}]
            )

            parsed_scenes = []
            lines = [
                line.strip()
                for line in res_scenes["message"]["content"].splitlines()
                if line.strip()
            ]

            for i, line in enumerate(lines[:8]):
                keyword = self.clean_keyword(line)
                if keyword:
                    parsed_scenes.append(
                        {
                            "scene_number": i + 1,
                            "stock_keywords": [keyword],
                            "visual_intent": "context",
                        }
                    )

            # Ensure minimum scenes
            if len(parsed_scenes) < 4:
                defaults = [
                    "breaking news",
                    "technology abstract",
                    "shocked face",
                    "money",
                ]
                for i in range(len(parsed_scenes), 4):
                    parsed_scenes.append(
                        {
                            "scene_number": i + 1,
                            "stock_keywords": [defaults[i]],
                            "visual_intent": "fallback",
                        }
                    )

            self.db.collection.update_one(
                {"_id": task["_id"]},
                {
                    "$set": {
                        "script": clean_script,
                        "scenes": parsed_scenes,
                        "status": "scripted",
                    }
                },
            )
            print(f"✅ Script generated ({len(clean_script.split())} words).")

        except Exception as e:
            print(f"❌ Brain Error: {e}")
