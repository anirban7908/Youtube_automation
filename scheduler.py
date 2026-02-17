import schedule
import time
import subprocess
import datetime
import sys

# Define the python executable (uses the current venv)
PYTHON_EXEC = sys.executable


def job(slot):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n🔔 [{timestamp}] TRIGGERING AUTOMATION: {slot.upper()}")

    try:
        # 1. Run the Creation Pipeline (main.py)
        # We run it as a subprocess to keep memory clean
        subprocess.run([PYTHON_EXEC, "-m", "core.main", slot], check=True)

        # 2. Run the Uploader
        print(f"🚀 [{timestamp}] Starting Upload...")
        subprocess.run([PYTHON_EXEC, "-m", "core.uploader"], check=True)

        print(f"✅ [{slot.upper()}] JOB FINISHED.")

    except subprocess.CalledProcessError as e:
        print(f"❌ ERROR in {slot} job: {e}")


# --- 📅 THE SCHEDULE ---
# Adjust times as needed
schedule.every().day.at("09:00").do(job, slot="morning")  # Motivation
schedule.every().day.at("13:00").do(job, slot="noon")  # Space
schedule.every().day.at("18:00").do(job, slot="evening")  # Nature
schedule.every().day.at("22:00").do(job, slot="night")  # History

print("===================================================")
print("🤖 THE KNOWLEDGE SPECTRUM: AUTOPILOT ENGAGED")
print("   - Schedule: 4 Times Daily")
print("   - Press Ctrl+C to stop")
print("===================================================")

# Immediate check (Optional: Remove if you don't want to test right now)
# job("noon")

while True:
    schedule.run_pending()
    time.sleep(60)  # Check every minute
