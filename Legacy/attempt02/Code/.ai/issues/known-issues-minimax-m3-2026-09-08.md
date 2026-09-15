# Отчёт по ошибкам в проекте KaizenSpeech

Я изучил все исходные файлы (`data_level.py`, `flywheel.py`, `system_level.py`, `ui_level.py`), файл зависимостей и тесты. В проекте есть специальный файл `Tests/test_known_issues.py`, в котором через `xfail(strict=True)` зафиксированы **известные, но намеренно не исправленные** баги — это документированные дефекты. Я подтвердил их все запуском pytest (6 xfailed, 1 passed).

## Подтверждённые ошибки (все воспроизводятся)

### 🔴 Issue 9 — ValueError на повреждённой записи в repetitions.json
**Файл:** `data_level.py:91-106` (`determine_next_phrase`)
Любая запись с битым `time_to_repeat` роняет всё приложение:
```
ValueError: time data 'not-a-date' does not match format '%Y.%m.%d %H:%M:%S'
```
Нет `try/except` вокруг `datetime.strptime(...)`. Достаточно одной испорченной записи, чтобы сессия упала.

### 🔴 Issue 3 — SM-2 не перепланирует фразу после ошибки
**Файл:** `data_level.py:249-265` (`_supermemo2`)
После неудачного ответа (`user_result=0.0`) ресет `repetition_number=0`, но **`time_to_repeat` остаётся прежним** (в тесте проверялось, что фраза, запланированная через 300 дней, останется через 300 дней). Должна быть перенесена на сегодня/завтра.

### 🟠 Issue 21 — пропущенная пунктуация не подсвечивается как ошибка
**Файл:** `data_level.py:191-229` (`find_user_mistakes`) и `ui_level.py:42-55`
Если пользователь ответил `tequiero` вместо `te,quiero`, корректирующая карта показывает True на позиции запятой. Пользователь не получает обратной связи, что потерял знак препинания.

### 🟠 Issue 16 — строки комментариев с отступом не распознаются
**Файл:** `system_level.py:35-37` (`read_phrases`)
Проверка `string[0] != '#'` — ловит `#` только в самом начале строки. Строка `"   # comment || ignored\n"` считается обычной записью и порождает ложную фразу.

### 🟠 Issue 2 — табуляция удаляется вместо замены на пробел
**Файл:** `data_level.py:241`
Фильтр `if ch.isalnum() or ch in white_list` (`white_list` = `" ?!.,:;'¿¡"`) выкидывает `\t` (таб не входит в white_list и не alnum). Тест: `'a\tb'` → `'ab'` вместо ожидаемого `'a b'`. До этого даже не доходит код `user_input = ' '.join(user_input.split())`.

### 🟡 Issue 10 — двойной перевод строки на Windows
**Файл:** `ui_level.py:15, 24, 28, 32, 35`
`input()` добавляет `\n`, плюс `os.linesep` (`\r\n` на Windows) в `+ os.linesep` → получается `\r\n\n`. Только на Windows.

## Дополнительные проблемы (не покрыты тестами)

### ⚠️ flywheel.py:30-33 — ошибка записи файла обнаруживается слишком поздно
```python
if is_merged and not fop.save_json_to_file(repetitions_file_path, repetitions):
    save_failed = True
```
Проверка срабатывает **только если данные изменились** (`is_merged=True`). Если файл повреждён, а фразы в словаре не менялись (например, повторный запуск), `save_failed` останется `False`, и сессия начнётся — пользователь будет отвечать, и только **после первого ответа** ошибка всплывёт.

### ⚠️ flywheel.py:38-39 — KeyError на пустом словаре
Если `determine_next_phrase` вернёт `''` (ни одной фразы с подходящим временем), строка `repetitions[current_phrase]` упадёт с `KeyError`. В текущей логике не достигается, но защиты нет.

### ⚠️ flywheel.py / ui_level.py — нет обработки EOFError
Если stdin закрывается (например, скрипт запущен в пайпе без данных), `input()` в `ui_level.user_session` бросит `EOFError`, который не ловится. `KeyboardInterrupt` ловится, `EOFError` — нет.

### ⚠️ system_level.py:19 — `os.walk(Path(__file__).parents[parents_level_up])`
При запуске из `Code/flywheel.py`, `parents_level_up=2` указывает на `github-pinned-repos/` и рекурсивно сканирует все репозитории в поисках, например, `phrases.txt`. Это и есть причина Issue 22 (упоминается в комментарии теста `test_flywheel.py:29`): можно случайно подцепить чужие данные разработчика, а не локальные. В тестах это обходят явным `cwd=tmp_path`, но дефект архитектуры остаётся.

### ⚠️ data_level.py:62 — `updated_phrases_num` инкрементируется для новых фраз
```python
if native_part not in repetitions:
    repetitions[native_part] = {...}   # +1 к added_phrases_num
    added_phrases_num += 1

if repetitions[native_part]['translations'] != english_part:
    repetitions[native_part]['translations'] = english_part
    updated_phrases_num += 1
```
Только что добавленная фраза тут же проверяется на обновление, и `english_part` гарантированно совпадает с только что записанным значением, так что `updated_phrases_num` не растёт — но визуально код читается так, будто может. Логической ошибки нет, но двойной проход стоит упростить.

## Что НЕ является ошибкой (проверил отдельно)
- ✅ Issue 1 (сохранение статистики по пути, а не по имени файла) — тест `test_flywheel_saves_statistics_by_path` проходит.
- ✅ Issue 24 (атомарное сохранение через `tempfile` + `os.replace`) — реализовано в `system_level.py:97-137`.
- ✅ Issue 28 (лимит длины фразы 300) — `max_phrase_len=300`, лишние фразы отбрасываются в `_split_into_phrases`.

## Резюме
В проекте **6 подтверждённых ошибок** (все помечены `xfail(strict=True)` в `Tests/test_known_issues.py`) и **4 дополнительных архитектурных риска**. Самые критичные — **Issue 9** (краш приложения на одной плохой записи) и **Issue 3** (неудачный ответ не возвращает фразу в расписание).