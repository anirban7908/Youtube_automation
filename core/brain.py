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
        source_url = task.get("source_url", "https://news.google.com")
        prompt = f"""
        ROLE: Documentary Director.
        TASK: Convert this news into a structured video script.
        SOURCE: "{source}"
        
        REQUIREMENTS:
        1. Break the story into 6-8 distinct SCENES.
        2. 'text': The narration for that scene (1-2 sentences).
        3. 'image_count': Should this scene have 1 image (slow) or 2 images (fast)? (Integer).
        4. **METADATA** (Generate this for YouTube):
           - 'title': A click-worthy, viral title (under 70 chars).
           - 'description': A compelling 3-sentence summary. PLAIN TEXT ONLY. NO HTML.
           - 'hashtags': A string of 3-5 relevant hashtags (e.g., "#Space #Science #Viral").
           - 'tags': A string of 5-10 comma-separated SEO tags.
        5. **CRITICAL - KEYWORD RULES (ZERO TOLERANCE)**:
           - 'keywords': A list of exactly 2 string search terms.
           - **NEVER leave this empty.** Even for the Outro/CTA scene.
           - **SPECIFICITY**: Use specific names (e.g., "Sony Camera", "Elon Musk", "SpaceX Rocket").
           - **FALLBACK**: If the scene is generic (like "Subscribe"), use keywords like ["Abstract Tech Background", "News Studio"].
           - **BAD**: [] or [""] -> THIS WILL CRASH THE SYSTEM.
           - **GOOD**: ["Sony LinkBuds", "Earbuds"] or ["Subscribe Button", "Social Media"].
        
        6. **CRITICAL - CTA RULES**: 
           - The FINAL SCENE must be a generic social media Call to Action.
           - Example: "Follow us for more {niche} stories and daily discoveries!"
           - **FORBIDDEN**: Do NOT say "Check out our full documentary", "Watch the full video", or "Link in bio". We do NOT have a full video. Keep it short.
        
        OUTPUT FORMAT (JSON ONLY):
        {{
            "title": "Viral Title Here",
            "description": "A short summary of the video content...",
            "hashtags": "#Tag1 #Tag2 #Tag3",
            "tags": "tag1, tag2, tag3, tag4",
            "scenes": [
                {{
                    "text": "Scientists have made a shocking discovery.",
                    "keywords": ["Scientist", "Lab"],
                    "image_count": 1
                }},
                {{
                    "text": "Follow us for more amazing science stories!",
                    "keywords": ["Abstract Background", "Community"],
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

            # 🟢 Combine scenes into one readable script
            # full_script = " ".join([scene["text"] for scene in data["scenes"]])

            # 🟢 NEW: Save Metadata to a Text File Immediately
            # We create a temporary folder since the final video folder doesn't exist yet
            meta_filename = f"metadata_{task['_id']}.txt"

            metadata_content = f"""
                ===================================================
                🚀 YOUTUBE UPLOAD METADATA
                ===================================================

                📌 TITLE:
                {data.get('title')}

                📝 DESCRIPTION:
                {data.get('description')}

                👇 Read the full story here:
                {source_url}

                ---------------------------------------------------
                🔥 HASHTAGS:
                {data.get('hashtags')}

                🏷️ TAGS:
                {data.get('tags')}
                ---------------------------------------------------
                """
            # Save to a temporary file (or specific log folder)
            with open(meta_filename, "w", encoding="utf-8") as f:
                f.write(metadata_content)

            print(f"📄 Metadata saved to: {meta_filename}")

            # Update Database
            self.db.collection.update_one(
                {"_id": task["_id"]},
                {
                    "$set": {
                        "script_data": data["scenes"],
                        # "full_script": full_script,
                        "title": data.get("title", task["title"]),
                        "ai_description": data.get("description"),
                        "ai_hashtags": data.get("hashtags"),
                        "ai_tags": data.get("tags"),
                        "status": "scripted",
                    }
                },
            )
            print(f"✅ Script Segmented: {len(data['scenes'])} scenes created.")

        except Exception as e:
            print(f"❌ Brain Error: {e}")
