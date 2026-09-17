import os
import sys
import yaml
from pathlib import Path

DEFAULT_CONFIG = {
    "paths": {
        "phrases": "Phrases/phrases.txt",
        "user_data": "user.json",
        "log_file": "app.log"
    },
    "user": {
        "name": "Михаил"
    },
    "languages": {
        "native": "русский",
        "foreign": "английский"
    },
    "fsrs": {
        "desired_retention": 0.9,
        "maximum_interval": 36500
    },
    "rating_thresholds": {
        "easy_max_errors": 1,
        "good_max_percent": 20.0,
        "hard_max_percent": 40.0,
        "again_min_errors": 9
    },
    "logging": {
        "level": "INFO",
        "max_bytes": 1048576,
        "backup_count": 5
    },
    "messages": {
        "welcome": "Привет, {user}! Для выхода введите /exit",
        "legend": "Легенда: зелёный = верно, красный = ошибка, '_' = пропущенный/лишний пробел, пунктуация = не ошибка",
        "no_due_cards": "Срочных повторений нет, продолжаем обучение.",
        "no_phrases": "Нет фраз для изучения.",
        "prompt_translation": "Переведите на {foreign}: ",
        "prompt_first_show": "Обучающий показ:\n{native} -> {foreign_first}",
        "prompt_repeat": "Повторите ввод: ",
        "confirm_delete_card": "Карточка '{native}' удалена из phrases.txt. Удалить её безвозвратно из базы? (y/n): ",
        "confirm_recreate_user_json": "Файл {user_file} повреждён. Пересоздать его (старый будет сохранён в бэкап)? (y/n): ",
        "card_deleted": "Карточка '{native}' удалена.",
        "card_kept": "Карточка '{native}' сохранена.",
        "session_end": "Сессия завершена. До встречи, {user}!"
    }
}

def validate_config(cfg: dict) -> list[str]:
    errors = []
    if not isinstance(cfg, dict):
        return ["Конфигурация должна быть объектом/словарём"]

    # Check paths
    paths = cfg.get("paths")
    if not isinstance(paths, dict):
        errors.append("Секция 'paths' отсутствует или не является словарём")
    else:
        for key in ("phrases", "user_data", "log_file"):
            if not isinstance(paths.get(key), str) or not paths.get(key).strip():
                errors.append(f"В секции 'paths' отсутствует или пуст путь '{key}'")

    # Check user
    user = cfg.get("user")
    if not isinstance(user, dict) or not isinstance(user.get("name"), str):
        errors.append("В секции 'user' отсутствует или некорректно имя 'name'")

    # Check languages
    langs = cfg.get("languages")
    if not isinstance(langs, dict):
        errors.append("Секция 'languages' отсутствует или некорректна")
    else:
        for key in ("native", "foreign"):
            if not isinstance(langs.get(key), str) or not langs.get(key).strip():
                errors.append(f"В секции 'languages' отсутствует поле '{key}'")

    # Check fsrs
    fsrs = cfg.get("fsrs")
    if not isinstance(fsrs, dict):
        errors.append("Секция 'fsrs' отсутствует или некорректна")
    else:
        dr = fsrs.get("desired_retention")
        if not isinstance(dr, (int, float)) or not (0 < dr <= 1):
            errors.append("Параметр 'fsrs.desired_retention' должен быть числом от 0 до 1")
        mi = fsrs.get("maximum_interval")
        if not isinstance(mi, int) or mi <= 0:
            errors.append("Параметр 'fsrs.maximum_interval' должен быть положительным целым числом")

    # Check rating thresholds
    thresh = cfg.get("rating_thresholds")
    if not isinstance(thresh, dict):
        errors.append("Секция 'rating_thresholds' отсутствует или некорректна")
    else:
        for key in ("easy_max_errors", "again_min_errors"):
            if not isinstance(thresh.get(key), int) or thresh.get(key) < 0:
                errors.append(f"Параметр 'rating_thresholds.{key}' должен быть неотрицательным целым числом")
        for key in ("good_max_percent", "hard_max_percent"):
            if not isinstance(thresh.get(key), (int, float)) or thresh.get(key) < 0:
                errors.append(f"Параметр 'rating_thresholds.{key}' должен быть неотрицательным числом")

    # Check logging
    log_cfg = cfg.get("logging")
    if not isinstance(log_cfg, dict):
        errors.append("Секция 'logging' отсутствует или некорректна")
    else:
        lvl = log_cfg.get("level")
        valid_levels = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
        if not isinstance(lvl, str) or lvl.upper() not in valid_levels:
            errors.append(f"Параметр 'logging.level' должен быть одним из: {', '.join(valid_levels)}")
        if not isinstance(log_cfg.get("max_bytes"), int) or log_cfg.get("max_bytes") <= 0:
            errors.append("Параметр 'logging.max_bytes' должен быть положительным целым числом")
        if not isinstance(log_cfg.get("backup_count"), int) or log_cfg.get("backup_count") < 0:
            errors.append("Параметр 'logging.backup_count' должен быть неотрицательным целым числом")

    # Check messages
    msgs = cfg.get("messages")
    if not isinstance(msgs, dict):
        errors.append("Секция 'messages' отсутствует или некорректна")

    return errors

def load_or_create_config(config_path: str = "config.yaml") -> dict:
    path = Path(config_path)
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(DEFAULT_CONFIG, f, allow_unicode=True, sort_keys=False, width=500)
        return DEFAULT_CONFIG

    try:
        with open(path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
    except Exception as e:
        print(f"Ошибка чтения конфигурационного файла '{config_path}': {e}")
        sys.exit(1)

    errors = validate_config(cfg)
    if errors:
        print(f"Конфигурационный файл '{config_path}' содержит ошибки:")
        for err in errors:
            print(f"  - {err}")
        sys.exit(1)

    return cfg
