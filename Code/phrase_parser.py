import sys
from pathlib import Path

class PhraseParseError(Exception):
    def __init__(self, errors: list[str]):
        super().__init__("\n".join(errors))
        self.errors = errors

def parse_phrases_file(file_path: str) -> list[tuple[str, list[str]]]:
    path = Path(file_path)
    if not path.exists():
        print(f"Файл со словарем не найден: {file_path}")
        sys.exit(1)

    errors = []
    seen_native: dict[str, int] = {}
    phrases: list[tuple[str, list[str]]] = []

    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception as e:
        print(f"Ошибка открытия файла '{file_path}': {e}")
        sys.exit(1)

    for line_num, raw_line in enumerate(lines, start=1):
        # Strip comments
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue

        pipe_double_count = line.count("||")
        if pipe_double_count == 0:
            errors.append(f"Строка {line_num}: отсутствует '||'")
            continue
        elif pipe_double_count > 1:
            errors.append(f"Строка {line_num}: более одного '||' в строке")
            continue

        parts = line.split("||")
        native_raw = parts[0]
        foreign_raw = parts[1]

        # Normalize native: collapse multiple spaces and trim
        native = " ".join(native_raw.split())
        if not native:
            errors.append(f"Строка {line_num}: пустая native-часть")
            continue

        # Split foreign variants
        variants_parts = foreign_raw.split("|")
        variants = []
        has_empty_variant = False

        for v_raw in variants_parts:
            v_norm = " ".join(v_raw.split())
            if not v_norm:
                has_empty_variant = True
            else:
                variants.append(v_norm)

        if has_empty_variant:
            errors.append(f"Строка {line_num}: пуст хотя бы один из вариантов перевода")
            continue

        if not variants:
            errors.append(f"Строка {line_num}: все варианты перевода пусты")
            continue

        if native in seen_native:
            errors.append(
                f"Строка {line_num}: дубликат native-фразы '{native}' "
                f"(ранее на строке {seen_native[native]})"
            )
            continue

        seen_native[native] = line_num
        phrases.append((native, variants))

    if errors:
        print(f"Ошибки в файле '{file_path}':")
        for err in errors:
            print(f"  - {err}")
        sys.exit(1)

    return phrases
