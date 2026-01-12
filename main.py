import asyncio
from core.scraper import NewsScraper
from core.brain import ScriptGenerator
from core.voice import VoiceEngine
from core.visuals import VisualScout
from core.assembler import VideoAssembler


async def run_pipeline():
    print("🚀 Starting YouTube Automation Pipeline")

    # STEP 1: Scrape News (Uncommented so you actually get data)
    try:
        NewsScraper().scrape_google_tech_news()
    except Exception as e:
        print(f"⚠️ Scraper warning: {e}")

    # STEP 2: Generate Script + Scene Storyboard
    ScriptGenerator().generate_script()

    # STEP 3: Generate AI Voice
    await VoiceEngine().generate_audio()

    # STEP 4: Download Scene-Based Visuals
    VisualScout().download_visuals()

    # STEP 5: Assemble Final Video
    VideoAssembler().assemble()

    print("✅ Pipeline completed successfully")


if __name__ == "__main__":
    asyncio.run(run_pipeline())
