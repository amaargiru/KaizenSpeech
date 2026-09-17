import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from fsrs import Card

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def ask_confirm(prompt: str, default: bool = False) -> bool:
    try:
        reply = input(prompt).strip().lower()
        if not reply:
            return default
        return reply in ('y', 'yes', 'д', 'да')
    except (EOFError, KeyboardInterrupt):
        print()
        return False

def save_user_data(file_path: str, data: dict) -> None:
    """Atomically saves user data using a temporary file in the same directory."""
    path = Path(file_path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(f".tmp_{os.getpid()}")
    try:
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(temp_path, path)
    except Exception as e:
        if temp_path.exists():
            try:
                temp_path.unlink()
            except Exception:
                pass
        raise IOError(f"Не удалось сохранить файл '{file_path}': {e}") from e

def load_user_data(file_path: str, messages: dict) -> dict:
    path = Path(file_path).resolve()
    if not path.exists():
        initial_data = {
            "schema_version": 1,
            "cards": {}
        }
        save_user_data(file_path, initial_data)
        return initial_data

    is_valid = False
    data = None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and data.get("schema_version") == 1 and isinstance(data.get("cards"), dict):
            is_valid = True
    except Exception:
        is_valid = False

    if not is_valid:
        prompt = messages.get(
            "confirm_recreate_user_json",
            "Файл {user_file} повреждён. Пересоздать его (старый будет сохранён в бэкап)? (y/n): "
        ).format(user_file=file_path)

        if ask_confirm(prompt, default=False):
            # Make backup
            timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = path.with_name(f"{path.name}.corrupt_{timestamp_str}.bak")
            try:
                shutil.copy2(path, backup_path)
                print(f"Старый файл сохранён в резервную копию: {backup_path}")
            except Exception as e:
                print(f"Предупреждение: не удалось создать бэкап: {e}")

            fresh_data = {
                "schema_version": 1,
                "cards": {}
            }
            save_user_data(file_path, fresh_data)
            return fresh_data
        else:
            print("Работа программы завершена пользователем.")
            sys.exit(1)

    return data

def sync_cards(user_data: dict, parsed_phrases: list[tuple[str, list[str]]],
               messages: dict, phrases_file: str, user_file: str, logger) -> dict:
    existing_cards = user_data["cards"]
    phrases_dict = {native: variants for native, variants in parsed_phrases}

    # 1. Handle deleted phrases
    for native in list(existing_cards.keys()):
        if native not in phrases_dict:
            prompt = messages.get(
                "confirm_delete_card",
                "Карточка '{native}' удалена из phrases.txt. Удалить её безвозвратно? (y/n): "
            ).format(native=native, phrases_file=phrases_file, user_file=user_file)

            if ask_confirm(prompt, default=False):
                del existing_cards[native]
                msg = messages.get("card_deleted", "Карточка '{native}' удалена.").format(native=native)
                print(msg)
                logger.info("Card '%s' removed from storage upon user confirmation.", native)
            else:
                msg = messages.get("card_kept", "Карточка '{native}' сохранена.").format(native=native)
                print(msg)
                logger.info("Card '%s' kept in storage despite removal from phrases file.", native)

    # 2. Handle added phrases & updated translation variants
    for native, variants in parsed_phrases:
        if native not in existing_cards:
            fsrs_card = Card()
            new_card = {
                "native": native,
                "foreign_variants": variants,
                "first_show": True,
                "fsrs_state": fsrs_card.to_dict(),
                "created_at": utc_now_iso(),
                "last_shown_at": None,
                "counters": {
                    "shows": 0,
                    "success": 0,
                    "fail": 0
                },
                "history": []
            }
            existing_cards[native] = new_card
            logger.info("Added new card: '%s'", native)
        else:
            card = existing_cards[native]
            if card.get("foreign_variants") != variants:
                old_variants = card.get("foreign_variants")
                card["foreign_variants"] = variants
                logger.info("Updated variants for card '%s': %s -> %s", native, old_variants, variants)

    save_user_data(user_file, user_data)
    return user_data
