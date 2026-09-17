import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from colorama import init

from config_manager import load_or_create_config
from phrase_parser import parse_phrases_file
from storage import load_user_data, sync_cards
from session import run_session

# Ensure UTF-8 for console I/O on all platforms (especially Windows)
try:
    if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')
    if sys.stderr.encoding and sys.stderr.encoding.lower() != 'utf-8':
        sys.stderr.reconfigure(encoding='utf-8')
    if sys.stdin.encoding and sys.stdin.encoding.lower() != 'utf-8':
        sys.stdin.reconfigure(encoding='utf-8')
except Exception:
    pass

def setup_logging(config: dict) -> logging.Logger:
    log_cfg = config.get("logging", {})
    paths_cfg = config.get("paths", {})
    log_file = paths_cfg.get("log_file", "app.log")
    level_name = log_cfg.get("level", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    max_bytes = int(log_cfg.get("max_bytes", 1048576))
    backup_count = int(log_cfg.get("backup_count", 5))

    # Ensure log directory exists
    log_dir = os.path.dirname(os.path.abspath(log_file))
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)

    logger = logging.getLogger("speech_trainer")
    logger.setLevel(level)

    # Avoid duplicate handlers if setup_logging is called multiple times
    if not logger.handlers:
        handler = RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8"
        )
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger

def main() -> None:
    init(autoreset=True)

    # Step 1: Load or create configuration
    config = load_or_create_config("config.yaml")

    # Step 2: Initialize logging
    logger = setup_logging(config)
    logger.info("Application started. Config loaded.")

    paths = config.get("paths", {})
    phrases_path = paths.get("phrases", "Phrases/phrases.txt")
    user_data_path = paths.get("user_data", "user.json")
    messages = config.get("messages", {})

    # Step 3: Read and validate phrases.txt
    parsed_phrases = parse_phrases_file(phrases_path)
    if not parsed_phrases:
        msg = messages.get("no_phrases", "Нет фраз для изучения.")
        print(msg)
        logger.warning("Phrases file is empty after parsing.")
        sys.exit(0)
    logger.info("Parsed %d phrases from '%s'.", len(parsed_phrases), phrases_path)

    # Step 4: Load user.json (with corruption check & backup)
    user_data = load_user_data(user_data_path, messages)
    logger.info("User data loaded from '%s'.", user_data_path)

    # Step 5: Sync phrases.txt -> user.json
    user_data = sync_cards(
        user_data=user_data,
        parsed_phrases=parsed_phrases,
        messages=messages,
        phrases_file=phrases_path,
        user_file=user_data_path,
        logger=logger
    )

    # Step 6: Check for empty cards set
    if not user_data.get("cards"):
        msg = messages.get("no_phrases", "Нет фраз для изучения.")
        print(msg)
        logger.warning("No cards in user.json after synchronization.")
        sys.exit(0)

    # Step 7: Welcome, exit instructions, legend
    user_name = config.get("user", {}).get("name", "Пользователь")
    welcome_msg = messages.get(
        "welcome",
        "Привет, {user}! Для выхода введите /exit"
    ).format(user=user_name)
    print(welcome_msg)

    legend_msg = messages.get(
        "legend",
        "Легенда: зелёный = верно, красный = ошибка, '_' = пропущенный/лишний пробел, пунктуация = не ошибка"
    )
    print(legend_msg)
    print()

    # Step 8: Learning session
    run_session(config, user_data, logger)

if __name__ == "__main__":
    main()
