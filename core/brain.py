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
            print("❌ ERROR: Ollama is not running! Run 'ollama serve'.")
            return False

    def clean_script_text(self, text):
        """Removes stage directions, visual cues, and actor labels."""
        # Remove text in parentheses/brackets e.g. (Cut to black) or [Visual]
        text = re.sub(r"[\(\[].*?[\)\]]", "", text)

        # Remove labels like "Host:", "Narrator:", "Hook:", "Scene 1:"
        text = re.sub(
            r"^(Hook|Body|Deep Dive|Twist|CTA|Scene \d+|Narrator|Host|Shopper):",
            "",
            text,
            flags=re.MULTILINE,
        )

        # Remove asterisks often used for *emphasis* or *action*
        text = text.replace("*", "")

        # Remove extra whitespace
        return "\n".join([line.strip() for line in text.splitlines() if line.strip()])

    def generate_script(self):
        if not self.check_ollama():
            return

        task = self.db.collection.find_one({"status": "pending"})
        if not task:
            print("📭 No pending tasks.")
            return

        print(f"🧠 AI generating script for: {task['title']}")

        # ---------------- STEP 1: SCRIPT ----------------
        script_prompt = f"""
        You are a YouTuber. Write a 40-second script for this news:
        Topic: "{task['title']}"
        Context: "{task.get('content', '')}"

        STRICT RULES:
        1. Write ONLY the spoken words. 
        2. NO visual instructions like (Cut to...), NO scene labels like [Scene 1].
        3. Tone: Shocked, viral, fast-paced.
        4. Structure: Hook -> What Happened -> Why it Matters.
        """

        try:
            res_script = ollama.chat(
                model=self.model, messages=[{"role": "user", "content": script_prompt}]
            )
            raw_script = res_script["message"]["content"].strip()

            # Clean it aggressively
            clean_script = self.clean_script_text(raw_script)

            if not clean_script:
                print("❌ Error: Script was empty after cleaning.")
                return

            # ---------------- STEP 2: SCENES (Text Parsing) ----------------
            # Using simple text parsing is more reliable than JSON for small models
            scene_prompt = f"""
            Based on this script, list 5 visual scenes to search for on stock video sites.
            Script: "{clean_script}"

            Format each line exactly like this:
            KEYWORD | INTENT

            Example:
            empty store shelves | Showing the problem
            shocked person face | Reaction
            expired food label | Detail shot
            garbage bin | Waste context
            person holding receipt | Buying proof

            Provide exactly 5 lines.
            """

            res_scenes = ollama.chat(
                model=self.model, messages=[{"role": "user", "content": scene_prompt}]
            )
            raw_scenes = res_scenes["message"]["content"].strip()

            parsed_scenes = []
            for i, line in enumerate(raw_scenes.splitlines()):
                if "|" in line:
                    parts = line.split("|")
                    keyword = parts[0].strip()
                    intent = parts[1].strip() if len(parts) > 1 else "background"

                    # Clean keyword to be simple
                    keyword = re.sub(r"[^\w\s]", "", keyword)

                    parsed_scenes.append(
                        {
                            "scene_number": i + 1,
                            "stock_keywords": [keyword],  # List format for visuals.py
                            "visual_intent": intent,
                        }
                    )

            # Fallback if parsing failed
            if not parsed_scenes:
                parsed_scenes = [
                    {
                        "scene_number": 1,
                        "stock_keywords": ["shocked face"],
                        "visual_intent": "Hook",
                    },
                    {
                        "scene_number": 2,
                        "stock_keywords": ["store shelves"],
                        "visual_intent": "Context",
                    },
                    {
                        "scene_number": 3,
                        "stock_keywords": ["receipt paper"],
                        "visual_intent": "Detail",
                    },
                    {
                        "scene_number": 4,
                        "stock_keywords": ["money waste"],
                        "visual_intent": "Impact",
                    },
                    {
                        "scene_number": 5,
                        "stock_keywords": ["question mark"],
                        "visual_intent": "CTA",
                    },
                ]

            # ---------------- STEP 3: SAVE ----------------
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
            print("✅ Script saved & Cleaned!")
            print(f"📜 Preview: {clean_script[:50]}...")
            print(f"🎬 Scenes: {[s['stock_keywords'][0] for s in parsed_scenes]}")

        except Exception as e:
            print(f"❌ ScriptGenerator Error: {e}")
