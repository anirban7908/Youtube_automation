import asyncio
import argparse
from datetime import datetime
from core.scraper import NewsScraper
from core.brain import ScriptGenerator
from core.voice import VoiceEngine
from core.visuals import VisualScout
from core.assembler import VideoAssembler
from core.verifier import VideoVerifier  # Don't forget this
from core.upload_prep import UploadManager  # <--- NEW


def get_current_time_slot():
    hour = datetime.now().hour
    if 5 <= hour < 12:
        return "morning"
    elif 12 <= hour < 17:
        return "noon"
    elif 17 <= hour < 21:
        return "evening"
    else:
        return "night"


async def run_pipeline(forced_slot=None):
    slot = forced_slot if forced_slot else get_current_time_slot()
    start_datetime = datetime.now()
    print(
        f"\n🚀 STARTING PIPELINE | Strategy Mode: {slot.upper()} | Start Time: {start_datetime}"
    )

    # 1. Scrape
    try:
        NewsScraper().scrape_targeted_niche(forced_slot=slot)
    except Exception as e:
        print(f"❌ Scraper Error: {e}")

    # 2. Script & SEO (Updated Brain)
    ScriptGenerator().generate_script()

    # 3. Voice
    await VoiceEngine().generate_audio()

    # 4. Visuals
    VisualScout().download_visuals()

    # 5. Assemble
    VideoAssembler().assemble()

    # 6. Verify (Quality Control)
    VideoVerifier().verify()

    # 7. Upload Prep (Metadata & Logging)
    UploadManager().prepare_package()

    end_time = datetime.now()
    print(f"\n✅ PIPELINE FINISHED | | End Time: {end_time}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--slot", type=str, help="Force: morning, noon, evening, night")
    args = parser.parse_args()
    asyncio.run(run_pipeline(forced_slot=args.slot))
