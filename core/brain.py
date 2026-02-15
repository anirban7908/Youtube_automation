import json
import re
import ollama
import time
from core.db_manager import DBManager


class ScriptGenerator:
    def __init__(self):
        self.db = DBManager()
        # 🟢 REVERTED TO SMART MODEL (Slower, but Higher Quality)
        self.model = "llama3.2:3b"

    def get_persona(self, niche):
        personas = {
            "finance": "You are a Wall Street Analyst. Tone: Urgent, Insightful. Focus on numbers.",
            "tech": "You are a Tech Reviewer. Tone: Fast-paced, Geeky. Focus on specific specs and tool names.",
            "sports": "You are a Sports Commentator. Tone: High Energy, Loud. Focus on player names and scores.",
            "history": "You are a Storyteller. Tone: Deep, Cinematic. Focus on dates and specific events.",
        }
        return personas.get(niche, personas["tech"])

    def extract_json(self, text):
        """
        🛠️ REPAIR TOOL: Even Llama 3 sometimes adds conversational filler.
        This extracts the JSON object if it's buried in text.
        """
        try:
            return json.loads(text)
        except:
            # Find the first '{' and last '}'
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(0))
                except:
                    pass
            return None

    def generate_script(self):
        task = self.db.collection.find_one({"status": "pending"})
        if not task:
            print("📭 No pending tasks to process.")
            return

        print(f"🧠 AI Architecting Video (Model: {self.model})...")
        print("   ⏳ This may take 2-5 minutes on CPU. Please wait...")

        system_persona = self.get_persona(task.get("niche", "tech"))

        # We feed it the first 2500 chars to ensure it gets all the list items
        source_content = task.get("content", "")[:2500]

        # 🟢 PROMPT: FORCES LONG SCRIPT & SPECIFIC DETAILS
        master_prompt = f"""
        {system_persona}
        SOURCE MATERIAL: "{source_content}"
        
        TASK: Write a YouTube Shorts Script (approx 160 words / 50-60 seconds).
        
        CRITICAL RULES:
        1. DO NOT just summarize. You MUST list specific names, dates, or tools found in the source.
        2. If the source lists "Top 10", pick the TOP 3 best ones and explain them briefly.
        3. Structure:
           - Hook (0-5s): Grab attention.
           - Body (5-50s): Deliver value. Mention specific names/tools.
           - Outro (50-60s): Ask a question.
        
        FORMAT: Return a SINGLE Valid JSON Object.
        {{
            "title": "Clickable Viral Title (Max 50 chars)",
            "script": "The full narration text. Must be long enough for 50 seconds.",
            "description": "3 sentence description for YouTube.",
            "tags": "tag1, tag2, tag3, tag4, tag5",
            "hashtags": "#tag1 #tag2 #tag3"
        }}
        """

        try:
            start_time = time.time()

            # Generate
            response = ollama.chat(
                model=self.model,
                format="json",  # Llama 3 supports this natively
                messages=[{"role": "user", "content": master_prompt}],
            )

            duration = time.time() - start_time
            print(f"   ✅ Generation Complete ({duration:.1f}s)")

            raw_content = response["message"]["content"]
            data = self.extract_json(raw_content)

            # Fallback if JSON fails (Rare with Llama 3, but possible)
            if not data:
                print("      ⚠️ JSON Parse Warning. Using Raw Text Fallback.")
                data = {
                    "title": task["title"][:50],
                    "script": raw_content.replace("{", "").replace("}", "")[:1000],
                    "description": f"Deep dive into {task['title']}",
                    "tags": "news, education, deep dive",
                    "hashtags": "#shorts",
                }

            clean_script = data.get("script", "")

            # Safety Check: If script is too short, extend it
            if len(clean_script.split()) < 60:
                print("      ⚠️ Script was too short. Extending outro...")
                clean_script += " This topic is developing fast. We will cover the full details in our next video, so make sure to subscribe. What are your thoughts on this? Let us know below."

            # 2. Generate Visual Scenes (8 Scenes for longer video)
            print("   🎨 Brainstorming 8 Visual Scenes...")
            scene_prompt = f"Create 8 distinct, highly detailed visual image prompts to match this script: {clean_script[:500]}"
            res_scenes = ollama.chat(
                model=self.model, messages=[{"role": "user", "content": scene_prompt}]
            )

            final_scenes = []
            for line in res_scenes["message"]["content"].splitlines():
                if len(line) > 10 and not "Here" in line:
                    clean_line = re.sub(r"^\d+[\.\)\-\s]+", "", line).strip()
                    final_scenes.append({"image_prompt": clean_line})

            # 3. Save to DB
            self.db.collection.update_one(
                {"_id": task["_id"]},
                {
                    "$set": {
                        "script": clean_script,
                        "title": data.get("title", task["title"]),
                        "description": data.get("description", ""),
                        "tags": data.get("tags", ""),
                        "hashtags": data.get("hashtags", ""),
                        "scenes": final_scenes[:8],  # Limit to 8
                        "status": "scripted",
                    }
                },
            )
            print(f"✅ Success! Title: {data.get('title')}")

        except Exception as e:
            print(f"❌ Brain Error: {e}")
