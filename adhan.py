import requests
import schedule
import time
import subprocess
import json
import logging
import sys
import shutil
from pathlib import Path
from datetime import datetime, timedelta

# =========================
# PATH SETUP
# =========================
BASE_DIR = Path(__file__).parent
LOG_DIR = BASE_DIR / "logs"
CACHE_FILE = BASE_DIR / "cache.json"
CONFIG_FILE = BASE_DIR / "config.json"
AUDIO_DIR = BASE_DIR / "audio"

LOG_DIR.mkdir(parents=True, exist_ok=True)

# =========================
# LOGGING
# =========================
logging.basicConfig(
    filename=LOG_DIR / "adhan.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# =========================
# CHECK DEPENDENCIES
# =========================
if not shutil.which("mpg123"):
    raise SystemExit("mpg123 is not installed. Run: sudo apt install mpg123")

# =========================
# CONFIG
# =========================
def load_config():
    try:
        with open(CONFIG_FILE) as f:
            return json.load(f)
    except Exception as e:
        logging.critical(f"Failed to load config: {e}")
        raise SystemExit("Config file missing or invalid.")

# =========================
# API FETCH
# =========================
def get_prayer_times(config, retries=3):
    url = "https://api.aladhan.com/v1/timingsByCity"
    params = {
        "city": config["city"],
        "country": config["country"],
        "method": config.get("method", 2)
    }

    for attempt in range(retries):
        try:
            r = requests.get(url, params=params, timeout=10)
            r.raise_for_status()
            timings = r.json()["data"]["timings"]

            logging.info("Prayer times fetched successfully")
            return timings

        except Exception as e:
            logging.warning(f"Attempt {attempt+1} failed: {e}")
            time.sleep(5)

    logging.error("API failed, trying cached prayer times")

    try:
        return load_cached_times()
    except SystemExit:
        logging.critical("No internet and no cache available. Retrying in 60 seconds...")
        time.sleep(60)
        return get_prayer_times(config)

# =========================
# CACHE
# =========================
def save_cached_times(timings):
    with open(CACHE_FILE, "w") as f:
        json.dump(timings, f)

def load_cached_times():
    if CACHE_FILE.exists():
        with open(CACHE_FILE) as f:
            return json.load(f)

    logging.critical("No cached prayer times available")
    raise SystemExit("No prayer times available.")

# =========================
# AUDIO
# =========================
def play_adhan(prayer_name):
    logging.info(f"Playing adhan for {prayer_name}")

    audio_path = AUDIO_DIR / "Adzan Mekkah.mp3"

    if not audio_path.exists():
        logging.error(f"Audio file not found: {audio_path}")
        return

    subprocess.run(["mpg123", str(audio_path)])

def play_reminder(prayer_name):
    logging.info(f"Reminder before {prayer_name}")

    audio_path = AUDIO_DIR / "reminder.mp3"

    if not audio_path.exists():
        logging.warning("Reminder audio not found, skipping")
        return

    subprocess.run(["mpg123", str(audio_path)])

# =========================
# TIME HELPER
# =========================
def get_reminder_time(time_str, minutes_before=2):
    t = datetime.strptime(time_str, "%H:%M")
    reminder_time = t - timedelta(minutes=minutes_before)
    return reminder_time.strftime("%H:%M")

# =========================
# SCHEDULER
# =========================
def schedule_prayers():
    schedule.clear()

    config = load_config()
    timings = get_prayer_times(config)
    save_cached_times(timings)

    prayers = ["Fajr", "Dhuhr", "Asr", "Maghrib", "Isha"]

    for prayer in prayers:
        time_str = timings[prayer][:5]

        # Main adhan
        schedule.every().day.at(time_str).do(play_adhan, prayer_name=prayer)
        logging.info(f"Scheduled {prayer} at {time_str}")
        print(f"Scheduled {prayer} at {time_str}")

        # Reminder (2 minutes before)
        reminder_time = get_reminder_time(time_str, 2)

        # Handle cross-day edge case
        if reminder_time > time_str:
            logging.warning(f"Skipping reminder for {prayer} (cross-day issue)")
        else:
            schedule.every().day.at(reminder_time).do(play_reminder, prayer_name=prayer)
            logging.info(f"Reminder for {prayer} at {reminder_time}")
            print(f"Reminder for {prayer} at {reminder_time}")

    logging.info("=== DAILY REFRESH COMPLETE ===")

# =========================
# CLI MODES
# =========================
def show_prayer_times():
    config = load_config()
    timings = get_prayer_times(config)

    print("\n=== Today's Prayer Times (LIVE API) ===")
    for prayer in ["Fajr", "Dhuhr", "Asr", "Maghrib", "Isha"]:
        print(f"{prayer:8} : {timings[prayer]}")

def show_cached_times():
    timings = load_cached_times()

    print("\n=== Cached Prayer Times ===")
    for prayer in ["Fajr", "Dhuhr", "Asr", "Maghrib", "Isha"]:
        print(f"{prayer:8} : {timings[prayer]}")

# =========================
# MAIN
# =========================
def main():
    print("Adhan service starting...")
    logging.info("=== SERVICE STARTED ===")

    schedule_prayers()

    # Refresh daily
    schedule.every().day.at("00:01").do(schedule_prayers)

    while True:
        schedule.run_pending()
        time.sleep(15)

# =========================
# ENTRY POINT
# =========================
if __name__ == "__main__":
    if "--show" in sys.argv:
        show_prayer_times()
    elif "--cached" in sys.argv:
        show_cached_times()
    else:
        main()