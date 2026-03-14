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
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logging.info(f"ADHAN STARTED for {prayer_name} at {now}")

    audio_path = AUDIO_DIR / "Adzan Mekkah.mp3"

    if not audio_path.exists():
        logging.error(f"Audio file not found: {audio_path}")
        return

    subprocess.run(["mpg123", str(audio_path)])
    logging.info(f"ADHAN FINISHED for {prayer_name}")

def play_reminder(prayer_name):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logging.info(f"REMINDER triggered for {prayer_name} at {now}")

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
    today = datetime.now().date()

    # Prevent API spam by checking cache file date
    if CACHE_FILE.exists():
        cache_mtime = datetime.fromtimestamp(CACHE_FILE.stat().st_mtime).date()
        if cache_mtime == today:
            logging.info("Schedule already refreshed today — skipping API call")
            return

    schedule.clear()

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logging.info(f"=== REFRESHING DAILY PRAYER SCHEDULE at {now} ===")

    config = load_config()
    timings = get_prayer_times(config)
    save_cached_times(timings)

    prayers = ["Fajr", "Dhuhr", "Asr", "Maghrib", "Isha"]

    for prayer in prayers:
        time_str = timings[prayer][:5]
        
        schedule.every().day.at(time_str).do(play_adhan, prayer_name=prayer)
        logging.info(f"Scheduled {prayer} at {time_str}")
        
        reminder_time = get_reminder_time(time_str, 2)
        
        if reminder_time > time_str:
            logging.warning(f"Skipping reminder for {prayer} (cross-day issue)")
        else:
            schedule.every().day.at(reminder_time).do(play_reminder, prayer_name=prayer)
            logging.info(f"Reminder for {prayer} at {reminder_time}")
            
    logging.info(f"Schedule updated successfully for {today}")
    logging.info("=== DAILY REFRESH COMPLETE ===")

# =========================
# CLI MODES
# =========================
def show_prayer_times():
    config = load_config()
    timings = get_prayer_times(config)
    today = datetime.now().strftime("%A, %d %B %Y")

    print("\n=== Today's Prayer Times (LIVE API) ===")
    print(f"Location: {config['city']}, {config['country']}")
    print(f"Date: {today}\n")

    for prayer in ["Fajr", "Dhuhr", "Asr", "Maghrib", "Isha"]:
        print(f"{prayer:8} : {timings[prayer]}")

def show_cached_times():
    timings = load_cached_times()
    today = datetime.now().strftime("%A, %d %B %Y")

    print("\n=== Cached Prayer Times ===")
    print(f"Date: {today}\n")

    for prayer in ["Fajr", "Dhuhr", "Asr", "Maghrib", "Isha"]:
        print(f"{prayer:8} : {timings[prayer]}")

def show_status():
    config = load_config()
    timings = load_cached_times()

    now = datetime.now()
    today = now.strftime("%A, %d %B %Y")

    prayers = ["Fajr", "Dhuhr", "Asr", "Maghrib", "Isha"]

    next_prayer = None
    next_time = None

    for prayer in prayers:
        t = datetime.strptime(timings[prayer][:5], "%H:%M").replace(
            year=now.year,
            month=now.month,
            day=now.day
        )

        if t > now:
            next_prayer = prayer
            next_time = t
            break

    if next_prayer is None:
        next_prayer = "Fajr (tomorrow)"
        t = datetime.strptime(timings["Fajr"][:5], "%H:%M")
        next_time = t.replace(
            year=now.year,
            month=now.month,
            day=now.day
        ) + timedelta(days=1)

    countdown = next_time - now
    hours, remainder = divmod(int(countdown.total_seconds()), 3600)
    minutes, _ = divmod(remainder, 60)

    print("\n=== Adhan System Status ===")
    print(f"Location     : {config['city']}, {config['country']}")
    print(f"Date         : {today}")
    print("")
    print(f"Next Prayer  : {next_prayer}")
    print(f"Time         : {next_time.strftime('%H:%M')}")
    print(f"Countdown    : {hours:02d}h {minutes:02d}m")
    print("")
    print(f"Schedule Src : cache.json")
    
    if CACHE_FILE.exists():
        refresh_time = datetime.fromtimestamp(CACHE_FILE.stat().st_mtime)
        print(f"Last Refresh  : {refresh_time.strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        print("Last Refresh  : No cache yet")
        
# =========================
# MAIN
# =========================
def main():
    print("Adhan service starting...")
    logging.info("=== SERVICE STARTED ===")

    schedule_prayers()

    # Daily refresh
    schedule.every().day.at("00:01").do(schedule_prayers)

    # Retry every minute (for wifi outages)
    schedule.every(1).minutes.do(schedule_prayers)

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
    elif "--status" in sys.argv:
        show_status()
    else:
        main()