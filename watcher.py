import json
import logging
import shutil
import sys
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

import config
from excel_writer import ExcelWriteError, append_work_order
from extractor import ExtractionError, extract_from_image

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}


def setup_logging():
    handler = RotatingFileHandler(
        config.LOG_FILE, maxBytes=2 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    handler.setFormatter(
        logging.Formatter("%(asctime)s  %(levelname)s  %(message)s")
    )
    console = logging.StreamHandler()
    console.setFormatter(logging.Formatter("%(asctime)s  %(levelname)s  %(message)s"))
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(handler)
    root.addHandler(console)
    return logging.getLogger("work_order_automation")


def load_processed_log():
    if config.PROCESSED_LOG_FILE.exists():
        try:
            return set(json.loads(config.PROCESSED_LOG_FILE.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, TypeError, ValueError):
            return set()
    return set()


def record_processed(filename):
    processed = load_processed_log()
    processed.add(filename)
    config.PROCESSED_LOG_FILE.write_text(
        json.dumps(sorted(processed), indent=2), encoding="utf-8"
    )


def is_file_stable(path, seconds=config.STABILITY_CHECK_SECONDS):
    try:
        size1 = path.stat().st_size
        time.sleep(seconds)
        size2 = path.stat().st_size
        return size1 == size2
    except OSError:
        return False


def is_duplicate(path, processed_log):
    if (config.PROCESSED_DIR / path.name).exists():
        return True
    if path.name in processed_log:
        return True
    return False


def process_image(path, logger, processed_log):
    logger.info("Processing %s", path.name)
    try:
        if not is_file_stable(path):
            logger.warning("%s is still being copied, skipping this pass", path.name)
            return
    except OSError:
        logger.warning("Cannot access %s yet, skipping this pass", path.name)
        return

    try:
        data = extract_from_image(path)
    except ExtractionError as exc:
        destination = config.NEEDS_REVIEW_DIR / path.name
        try:
            shutil.move(str(path), str(destination))
        except OSError:
            destination = path
        logger.error(
            "[%s] EXTRACTION FAILED for %s -> needs review: %s",
            exc.tag,
            path.name,
            exc,
        )
        print(f"[needs review] {path.name}: {exc}")
        return

    try:
        append_work_order(data)
    except ExcelWriteError as exc:
        destination = config.NEEDS_REVIEW_DIR / path.name
        try:
            shutil.move(str(path), str(destination))
        except OSError:
            destination = path
        logger.error("EXCEL FAILED for %s -> needs review: %s", path.name, exc)
        print(f"[needs review] {path.name}: {exc}")
        return

    record_processed(path.name)
    processed_log.add(path.name)
    try:
        shutil.move(str(path), str(config.PROCESSED_DIR / path.name))
    except OSError as exc:
        logger.error("Could not move %s to processed/: %s", path.name, exc)
        print(f"[error] Could not move {path.name}: {exc}")
        return

    logger.info("SUCCESS %s -> processed (WO %s)", path.name, data["work_order"])
    print(f"[success] {path.name}: Work Order {data['work_order']} added to Excel")


class ImageHandler(FileSystemEventHandler):
    def __init__(self, logger):
        self.logger = logger
        self.processed_log = load_processed_log()
        self._last_seen = {}

    def on_created(self, event):
        if event.is_directory:
            return
        self._handle(event.src_path)

    def on_moved(self, event):
        if not event.is_directory and event.dest_path:
            self._handle(event.dest_path)

    def _handle(self, src_path):
        path = Path(src_path)
        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            return
        now = time.time()
        if self._last_seen.get(path.name, 0) > now - 5:
            return
        self._last_seen[path.name] = now
        time.sleep(1)
        process_image(path, self.logger, self.processed_log)


def process_existing_files(logger, processed_log):
    for path in sorted(config.DATA_DIR.iterdir()):
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS:
            if is_duplicate(path, processed_log):
                continue
            process_image(path, logger, processed_log)


def main():
    logger = setup_logging()

    if not config.get_api_key():
        message = (
            "ERROR: GEMINI_API_KEY is not set.\n"
            "1. Open a Command Prompt and run:\n"
            "     setx GEMINI_API_KEY \"your-key-here\"\n"
            "2. Close and reopen the terminal (or restart run.bat)."
        )
        print(message)
        logger.error("Startup blocked: GEMINI_API_KEY not set")
        sys.exit(1)

    try:
        from google import genai  # noqa: F401
        import openpyxl  # noqa: F401
        import watchdog  # noqa: F401
    except ImportError:
        message = (
            "ERROR: Dependencies are missing.\n"
            "Run this in a Command Prompt inside the project folder:\n"
            "     pip install -r requirements.txt"
        )
        print(message)
        logger.error("Startup blocked: missing dependencies")
        sys.exit(1)

    processed_log = load_processed_log()

    print("=" * 60)
    print(" Work Order Traveler -> Excel Automation")
    print(f" Watching: {config.DATA_DIR}")
    print(f" Output:   {config.EXCEL_FILE}")
    print(" Drop new photos into the data/ folder.")
    print(" Press Ctrl+C to stop.")
    print("=" * 60)

    process_existing_files(logger, processed_log)

    observer = Observer()
    observer.schedule(
        ImageHandler(logger), str(config.DATA_DIR), recursive=False
    )
    observer.start()
    logger.info("Watcher started on %s", config.DATA_DIR)
    try:
        while True:
            time.sleep(config.POLL_INTERVAL_SECONDS)
    except KeyboardInterrupt:
        observer.stop()
        logger.info("Watcher stopped by user")
    observer.join()


if __name__ == "__main__":
    main()
