import json
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

    def hard_clean_prompt(self, text):
        """Removes banned words and conversational filler."""
        text = re.sub(
            r"^(Here is|I can|Sure|The prompt is).+?:", "", text, flags=re.IGNORECASE
        )
        banned = [
            "bikini",
            "swimsuit",
            "underwear",
            "lingerie",
            "naked",
            "nude",
            "blood",
            "gore",
            "kill",
            "murder",
            "weapon",
            "gun",
            "knife",
            "drug",
            "cocaine",
            "terror",
            "bomb",
        ]
        for word in banned:
            text = re.sub(rf"\b{word}\b", "", text, flags=re.IGNORECASE)
        return text.strip()[:300]

    def generate_script(self):
        if not self.check_ollama():
            return

        task = self.db.collection.find_one({"status": "pending"})
        if not task:
            print("📭 No pending tasks.")
            return

        print(f"🧠 AI generating script for: {task['title']}")

        # 1. Script Generation (STRICT NARRATOR MODE)
        script_prompt = f"""
        You are a Tech News Narrator.
        SOURCE: "{task.get('content', '')}"
        
        TASK: Write a 50s script (approx 130 words) summarizing this news for a video.
        
        CRITICAL RULES:
        1. Write ONLY the spoken words. 
        2. NO "FADE IN", NO "INT.", NO Character Names (e.g. "Speaker:").
        3. NO Stage Directions (e.g. "(laughs)", "[music plays]").
        4. Write as a SINGLE NARRATOR speaking directly to the audience.
        
        STRUCTURE:
        - Hook: "Big news for [Topic]..."
        - Body: Explain what happened.
        - Why it matters: The impact.
        
        FORMAT: JSON Object with a "script" key.
        """

        try:
            res_script = ollama.chat(
                model=self.model,
                format="json",
                messages=[{"role": "user", "content": script_prompt}],
            )
            script_json = json.loads(res_script["message"]["content"])
            clean_script = script_json.get("script", "")

            if not clean_script:
                raise ValueError("Empty script")

            # 2. Scene Generation (Plain List)
            scene_prompt = f"""
            Script: "{clean_script}"
            
            TASK: Write 8 visual image descriptions to match this script.
            RULES:
            1. One scene per line.
            2. Describe the IMAGE only (e.g. "A futuristic podcast studio", "Michael Irvin holding a football").
            3. NO scene numbers or bullet points.
            
            Example Output:
            A close up of a microphone with neon lights
            A football stadium at night
            """

            res_scenes = ollama.chat(
                model=self.model, messages=[{"role": "user", "content": scene_prompt}]
            )
            raw_text = res_scenes["message"]["content"].strip()

            final_scenes = []
            lines = raw_text.splitlines()
            valid_lines = [
                line.strip()
                for line in lines
                if len(line) > 10 and not line.lower().startswith("here")
            ]

            for i, line in enumerate(valid_lines[:8]):
                clean_line = re.sub(r"^\d+[\.\)\-\s]+", "", line).strip()
                # Clean prompt using our hard filter
                safe_prompt = self.hard_clean_prompt(clean_line)

                final_scenes.append(
                    {"scene_number": i + 1, "image_prompt": safe_prompt}
                )

            self.db.collection.update_one(
                {"_id": task["_id"]},
                {
                    "$set": {
                        "script": clean_script,
                        "scenes": final_scenes,
                        "status": "scripted",
                    }
                },
            )
            print(f"✅ Success: Generated {len(final_scenes)} Narrator-Style Scenes.")

        except Exception as e:
            print(f"❌ Brain Error: {e}")
