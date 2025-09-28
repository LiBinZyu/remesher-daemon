import os
import sys
import time
import logging
import yaml
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from db.database import add_task, get_next_task, update_status, init_db
from cleanup import cleanup_stale_tasks, cleanup_workdir
from pipeline import process_task

# --- Load config ---
with open("config.yaml", "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

input_dir = config["paths"]["input_dir"]
output_dir = config["paths"]["output_dir"]
work_dir = config["paths"]["work_dir"]
db_file = config["paths"]["database_file"]
sleep_interval = config.get("main_loop", {}).get("sleep_interval_seconds", 5)

# --- Setup logging ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("daemon.log", encoding="utf-8")
    ]
)
logger = logging.getLogger("remesher-daemon")

# --- Ensure DB is initialized ---
init_db(db_file)

# --- Cleanup stale tasks on startup ---
cleanup_stale_tasks()

# --- Watchdog handler ---
class ZipHandler(FileSystemEventHandler):
    def on_created(self, event):
        if not event.is_directory and event.src_path.lower().endswith(".zip"):
            logger.info(f"New zip detected: {event.src_path}")
            add_task(event.src_path)
            logger.info(f"Task added for: {event.src_path}")

def start_watchdog():
    event_handler = ZipHandler()
    observer = Observer()
    observer.schedule(event_handler, input_dir, recursive=False)
    observer.start()
    logger.info(f"Started watchdog on {input_dir}")
    return observer

def main_loop():
    logger.info("Remesher Daemon started.")
    observer = start_watchdog()
    try:
        while True:
            task = get_next_task()
            if task:
                uuid = task["uuid"]
                logger.info(f"Processing task: {uuid}")
                try:
                    update_status(uuid, "PROCESSING")
                    process_task(task)
                    update_status(uuid, "DONE")
                    logger.info(f"Task {uuid} completed successfully.")
                except Exception as e:
                    logger.error(f"Task {uuid} failed: {e}", exc_info=True)
                    update_status(uuid, "FAILED", str(e))
                # finally:
                #     cleanup_workdir(uuid)
            else:
                time.sleep(sleep_interval)
    except KeyboardInterrupt:
        logger.info("Daemon stopped by user.")
    finally:
        observer.stop()
        observer.join()

if __name__ == "__main__":
    main_loop()
