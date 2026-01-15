import asyncio
from core.scraper import NewsScraper
from core.brain import ScriptGenerator
from core.voice import VoiceEngine
from core.visuals import VisualScout
from core.assembler import VideoAssembler
from datetime import datetime

# Get the current date and time
start = datetime.now()

# Print only the time in a specific format (HH:MM:SS)
start_time = start.strftime("%H:%M:%S")
print("Start Time =", start_time)


async def run_pipeline():
    print("🚀 Starting YouTube Automation Pipeline")

    # STEP 1: Scrape News (Uncommented so you actually get data)
    try:
        NewsScraper().scrape_top_trends()
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

    # Get the current date and time
    start = datetime.now()
    end_time = start.strftime("%H:%M:%S")
    print("End Time =", end_time)


if __name__ == "__main__":
    asyncio.run(run_pipeline())
