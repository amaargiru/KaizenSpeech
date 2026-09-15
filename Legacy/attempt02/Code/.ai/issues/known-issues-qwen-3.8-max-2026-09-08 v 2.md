# Отчёт по анализу кода проекта Flywheel

**Дата анализа:** 08.09.2026
**Проанализированы:** `flywheel.py`, `data_level.py`, `system_level.py`, `ui_level.py`, `phrases.txt`
**Окружение:** Python 3.12.7 (Windows), `jellyfish 1.2.1`, `colorama 0.4.6`
**Методика:** статический анализ + инспекции IDE + **исполняемое воспроизведение** каждого дефекта
(стенд в `%TEMP%\fw_bugcheck`, файлы проекта не изменялись) + сквозной прогон приложения.

---

## Сводка найденных дефектов

| ID | Серьёзность | Файл:строки | Кратко | Подтв. |
|----|-------------|-------------|--------|:---:|
| B01 | 🔴 Критическая | `system_level.py:83-94`, `data_level.py:37-80` | Битый/пустой `repetitions.json` молча считается пустым словарём → история обучения стирается и перезаписывается | ✅ |
| B02 | 🔴 Критическая | `system_level.py:56-57`, `data_level.py:66-70` | Частичное чтение `phrases.txt` → `merge()` **удаляет** непрочитанные фразы из истории (800 → 290) | ✅ |
| B03 | 🔴 Критическая | `data_level.py:21-35` | `data_assessment()` не способен обнаружить сбой чтения и вызывает `sys.exit()` с кодом 0 | ✅ |
| B04 | 🟠 Высокая | `system_level.py:13-26` | `Path(__file__).parents[2]` → `IndexError`; неограниченный `os.walk` по `C:\Work`; подхват чужого файла | ✅ |
| B05 | 🟠 Высокая | `data_level.py:260-265` | При **неправильном** ответе `easiness_factor` растёт (2.500 → 2.571) — карточка «легчает» за провал | ✅ |
| B06 | 🟠 Высокая | `data_level.py:256-258` | Интервал не растёт геометрически (`6*EF` вместо `I(n-1)*EF`): после 30 идеальных ответов — 32 дня | ✅ |
| B07 | 🟠 Высокая | `data_level.py:260-261`, `103-106` | Проваленная карточка навсегда остаётся просроченной и **блокирует выдачу всех новых фраз** | ✅ |
| B08 | 🟠 Высокая | `data_level.py:186-188` | Акценты не нормализуются: `que es` против `Qué es?` = 0.82 → «Not bad» вместо «Correct!» | ✅ |
| B09 | 🟠 Высокая | `ui_level.py:15`, `flywheel.py:54` | `EOFError` из `input()` не обрабатывается → traceback при закрытом stdin | ✅ |
| B10 | 🟡 Средняя | `ui_level.py:44-55` | Неправильный пробел в первой/последней позиции эталона **не печатается** — показанный ответ короче настоящего (латентный) | ✅ |
| B11 | 🟡 Средняя | `data_level.py:219-222` | Порог `n >= 3` искажает разбор: `Yo` против `Y yo` — весь красный, `Lo está` против `Lo es` — весь зелёный | ✅ |
| B12 | 🟡 Средняя | `data_level.py:215` | `SequenceMatcher(isjunk=...)` — мёртвый код: `isjunk` применяется к `b`, а `b` уже без пунктуации | ✅ |
| B13 | 🟡 Средняя | `system_level.py:24-26`, `83-94` | Первый запуск: два пугающих «Cannot open or parse» для файлов, созданных самим приложением | ✅ |
| B14 | 🟡 Средняя | `system_level.py:15`, `24` | Файлы данных создаются в CWD, а `phrases.txt` ищется у приложения — асимметрия путей | ✅ |
| B15 | 🟡 Средняя | `data_level.py:62`, `93/98`, `119-153` | Нет валидации структуры записей: `KeyError`, `ValueError` (strptime), `TypeError` | ✅ |
| B16 | 🟡 Средняя | `flywheel.py:22` | `statistics` не проходит `data_assessment` → `TypeError` на первом же ответе | ✅ |
| B17 | 🟢 Низкая | `data_level.py:112` | `== max_attempts_len` вместо `>=` — при внешнем редактировании JSON список попыток перестаёт ограничиваться (11 → 12) | ✅ |
| B18 | 🟡 Средняя | `data_level.py:141-151`, `system_level.py:45`, `ui_level.py:15` | Языки перепутаны в именах: `english_words` содержит испанские слова | ✅ |
| B19 | 🟡 Средняя | `flywheel.py:49-60` | После сбоя записи сообщение об ошибке дублируется, причина остановки сессии не сообщается | ✅ |
| B20 | 🟢 Низкая | `system_level.py:39-41` | Off-by-one в тексте ошибки: «contains 3 "||" separators» при двух разделителях | ✅ |
| B21 | 🟢 Низкая | `system_level.py:36` | Комментарий с отступом (`   # ...`) парсится как данные | ✅ |
| B22 | 🟢 Низкая | `system_level.py:24` | Файл создаётся без `encoding='utf-8'`; `open()` без обработки ошибок → `FileNotFoundError` | ✅ |
| B23 | 🟢 Низкая | `ui_level.py:15,24,28,32,35` | `os.linesep` внутри `print()` даёт лишнюю пустую строку (`'Correct!\r\n\n'`) | ✅ |
| B24 | 🟢 Низкая | `flywheel.py:1` | Неверный shebang `#!/usr/bin/python3.12` | ✅ |
| B25 | 🟢 Низкая | `flywheel.py:73` | `sys.exit()` без кода → ошибка данных возвращает exit code 0 | ✅ |
| B26 | 🟢 Низкая | проект | Нет `requirements.txt`/`pyproject.toml`; интерпретатор IDE без `jellyfish`/`colorama` | ✅ |
| B27 | 🟢 Низкая | `system_level.py:127` | `save_json_to_file()` проглатывает `KeyboardInterrupt`; нет fsync каталога | ✅ |
| B28 | ⚪ Замечание | `data_level.py:52`, `system_level.py:52-55` | `translations` — то `str`, то `list`; один объект списка разделяется несколькими ключами | ✅ |
| B29 | ⚪ Замечание | `data_level.py:83-106`, `194-197` | Инвертированные имена переменных, dataclass внутри функции, смешение `List`/`list` | ✅ |

**Итого: 29 дефектов** — 3 критических, 6 высоких, 9 средних, 9 низких, 2 замечания.
26 из них воспроизведены фактическим запуском кода (вывод стенда приведён в описаниях),
3 (B24, B26, B29) подтверждены инспекцией кода и результатами сквозного прогона.

---

## 🔴 Критические дефекты (потеря пользовательских данных)

### B01. Повреждённый `repetitions.json` молча обнуляется и перезаписывается

**Где:** `system_level.py:83-94` (`read_json_from_file`), `data_level.py:37-80` (`merge`), `flywheel.py:19-20`

**Суть.** `read_json_from_file()` при любой ошибке (`JSONDecodeError`, `OSError`, `UnicodeDecodeError`)
печатает сообщение и возвращает `{}`. Вызывающий код не может отличить «файл пуст/не существует»
от «файл повреждён». Далее `data_assessment()` видит пустой словарь и разрешает работу,
а `merge()` пересоздаёт все карточки с нуля и **перезаписывает** повреждённый файл.

**Воспроизведение (фактический вывод стенда):**

```
Cannot open or parse ...\repetitions_bad.json file:
    JSONDecodeError("Expecting ',' delimiter: line 1 column 153 (char 152)")
loaded from the corrupted file -> {}
data_assessment -> can_work = True | msg = No data assessment errors
merge -> True | Added 2 new phrases
history after merge: {"I know": {... "easiness_factor": 2.5, "repetition_number": 0, "attempts": []}, ...}
save over the corrupted file -> True
```

До повреждения в файле было `repetition_number: 7`, `attempts: [["x", 1.0]]`, `time_to_repeat: 2020.01.01`.
После запуска — `0`, `[]`, текущая дата. **История уничтожена безвозвратно**: запись атомарная,
поэтому предыдущий вариант файла не сохраняется.

**Почему существующая защита не срабатывает.** Комментарий в `data_level.py:43-45` утверждает, что пустой
файл фраз трактуется как ошибка загрузки, «чтобы один плохой запуск не стёр все повторения».
Но ровно тот же сценарий не защищён со стороны `repetitions.json`: пустой словарь там считается нормой.

**Как исправить.** Различать «файла нет» и «файл не читается»:

```python
@staticmethod
def read_json_from_file(file_path: str) -> tuple[dict, bool]:
    """Возвращает (данные, ok). ok=False означает 'файл существует, но не прочитан'."""
    if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
        return {}, True                      # легитимно пусто
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return (data, True) if isinstance(data, dict) else ({}, False)
    except Exception as e:
        print(f'Cannot open or parse {file_path} file: {repr(e)}')
        return {}, False                     # повреждён — работать нельзя
```

В `flywheel.py` при `ok=False` — немедленно `sys.exit(1)` без вызова `merge()` и без записи.
Дополнительно стоит сохранять резервную копию (`repetitions.json.bak`) перед первой записью сессии.

---

### B02. Частичное чтение `phrases.txt` приводит к удалению валидных повторений

**Где:** `system_level.py:56-57` (`except Exception`), `data_level.py:66-70` (удаление фраз)

**Суть.** `read_phrases()` читает файл построчно внутри `try`. Исключение в середине файла
(неверный байт, обрыв, блокировка) прерывает итерацию, и функция возвращает **частичный** словарь.
`merge()` затем трактует все отсутствующие в нём фразы как «удалённые пользователем» и стирает
соответствующие повторения вместе с историей. Защита `if len(phrases) == 0` (`data_level.py:42`)
не помогает: словарь непустой, просто неполный.

**Воспроизведение** (файл 22 998 байт, 800 валидных строк, неверный байт `\xff\xfe` после 500-й):

```
Cannot open or parse ...\phrases_big_bad.txt file: UnicodeDecodeError('utf-8', ..., 6088, 6089, 'invalid start byte')
parsed phrases -> 290 of 800
contains "phrase 0"   -> True
contains "phrase 700" -> False
repetitions before merge -> 800
data_assessment -> can_work = True | msg = No data assessment errors
merge -> True | Removed 510 phrases
repetitions after merge  -> 290
```

**510 карточек с историей удалены**, после чего `flywheel.py:30` фиксирует результат на диске.
В текущем `phrases.txt` 70 строк — при росте словаря до сотен фраз риск становится практическим.

**Как исправить.** `read_phrases()` должна сообщать об успехе/провале и не отдавать частичные данные:

```python
except Exception as e:
    print(f'Cannot open or parse {file_path} file: {repr(e)}')
    return {}, False          # вместо частичного словаря
```

Дополнительная страховка в `merge()`: не удалять повторения, если из файла фраз исчезло подозрительно
много ключей (например, более 20 %), — вместо этого требовать явного подтверждения пользователем.

---

### B03. `data_assessment()` не выполняет свою задачу и ломает контракт вызова

**Где:** `data_level.py:21-35`, вызов в `flywheel.py:20`

**Суть.** Функция объявлена как «проверка данных перед работой» с контрактом `-> tuple[bool, str]`,
но в двух ветках вместо возврата результата вызывает `sys.exit()` без кода. Проверка типов
`isinstance(phrases, dict)` практически недостижима: `read_phrases()` и `read_json_from_file()`
всегда возвращают `dict` (пусть и пустой), поэтому **реальная причина отказа — сбой чтения —
не обнаруживается вовсе**. Именно это делает возможными B01 и B02.

**Воспроизведение:**

```
Cannot parse phrase file
  SystemExit raised from a "check" function, code = None
```

Кроме того, условие `len(phrases) == 0 and len(repetitions) == 0` срабатывает только когда пусты
**оба** словаря; если пуст лишь `phrases` (файл не прочитан), работа продолжается как ни в чём не бывало.

**Как исправить.** Не вызывать `sys.exit()` из функции-предиката: вернуть признак ошибки, а код выхода
устанавливать в `flywheel.py`. Добавить проверку структуры каждой записи (см. B15) и явный признак
«файл не прочитан» из B01/B02.

---

## 🟠 Высокая серьёзность

### B04. `find_or_create_file()`: `IndexError`, неограниченный обход диска и подхват чужого файла

**Где:** `system_level.py:13-26`

**Три самостоятельные проблемы в одной функции:**

1. **`IndexError` на «мелком» дереве каталогов.** `Path(__file__).parents[parents_level_up]`
   с `parents_level_up=2` требует, чтобы модуль лежал минимум в трёх уровнях от корня диска.
   Для `C:\proj\system_level.py` родителей всего два:
   ```
   parents available for C:\proj\system_level.py -> 2
   IndexError: 2
   ```
   Приложение падает на старте без внятной диагностики.

2. **Обход дерева, не относящегося к проекту.** В текущем расположении
   (`C:\Work\flywheel_temp\Code\system_level.py`) корнем поиска оказывается **`C:\Work` целиком** —
   `os.walk` рекурсивно обходит все проекты, виртуальные окружения и кэши. Это и медленно,
   и некорректно (см. п. 3).

3. **Подхват одноимённого файла из постороннего каталога.** Воспроизведение на стенде
   (копия приложения в `...\fw_bugcheck\projA\Code`, посторонний `phrases.txt` в
   `...\fw_bugcheck\projA\unrelated_backup`, запуск из `...\fw_bugcheck\run`):
   ```
   module file       : ...\fw_bugcheck\projA\Code\system_level.py
   walk root         : ...\fw_bugcheck
   cwd               : ...\fw_bugcheck\run
   phrases.txt in cwd: False
   RETURNED PATH     : ...\fw_bugcheck\projA\unrelated_backup\phrases.txt
   created a new file: False
   ```
   Загружена **чужая резервная копия** словаря. В связке с `merge()` (B02) это приводит к удалению
   актуальных повторений: приложение молча работает с устаревшим набором фраз.
   Порядок обхода `os.walk` не гарантирован, поэтому результат ещё и недетерминирован.

**Как исправить.** Искать только в предсказуемых местах и никогда — в произвольном поддереве:

```python
APP_DIR = Path(__file__).resolve().parent

@staticmethod
def find_or_create_file(filename: str) -> str:
    for candidate in (Path.cwd() / filename, APP_DIR / filename):
        if candidate.is_file():
            return str(candidate)
    target = APP_DIR / filename              # данные всегда рядом с приложением
    target.touch(exist_ok=True)
    return str(target)
```

Если поиск по проекту действительно нужен, ограничить его явным списком каталогов и глубиной
(пропуск `.venv`, `__pycache__`, `.git`) и логировать выбранный путь.

---

### B05. При неправильном ответе `easiness_factor` увеличивается

**Где:** `data_level.py:249-265` (`_supermemo2`)

**Суть.** Ветка «неправильный ответ» (`user_result < level_good = 0.97`) обнуляет `repetition_number`,
но формула пересчёта EF применяется **независимо** от ветки. Поскольку оценка непрерывна
(`q = 5 * user_result`), любой ответ с похожестю выше ~0.96 даёт положительную добавку к EF.
Карточка, которую пользователь **не сдал**, помечается как более лёгкая, и следующий интервал
для неё станет длиннее.

**Воспроизведение (кривая EF при стартовом значении 2.5):**

```
user_result=1.0        CORRECT branch -> EF 2.500 => 2.6000 (+0.1000)
user_result=0.97       CORRECT branch -> EF 2.500 => 2.5875 (+0.0875)
user_result=0.95       WRONG branch   -> EF 2.500 => 2.5787 (+0.0787)   <-- провал, но EF вырос
user_result=0.9333333  WRONG branch   -> EF 2.500 => 2.5711 (+0.0711)   <-- провал, но EF вырос
user_result=0.9        WRONG branch   -> EF 2.500 => 2.5550 (+0.0550)   <-- провал, но EF вырос
user_result=0.8        WRONG branch   -> EF 2.500 => 2.5000 ( 0.0000)
user_result=0.5        WRONG branch   -> EF 2.500 => 2.2750 (-0.2250)
```

Подтверждено и сквозным прогоном: в сохранённом `repetitions.json` карточка `"It is"` после ответа
с оценкой `0.9333` (вердикт «Not bad», `repetition_number: 0`) получила
`"easiness_factor": 2.571111111111111`.

В оригинальном SM-2 оценка `q` — целое 0…5, и EF растёт только при `q = 5`
(`q = 4` даёт ровно 0, `q <= 3` — отрицательную добавку). Непрерывное отображение `q = 5 * user_result`
ломает эту семантику.

**Как исправить.** Обновлять EF только в ветке правильного ответа:

```python
if user_result >= DataOperations.level_good:
    ...                                    # как сейчас
    repetition['easiness_factor'] += 0.1 - (5 - 5 * user_result) * (0.08 + (5 - 5 * user_result) * 0.02)
else:
    repetition['repetition_number'] = 0
    repetition['easiness_factor'] -= 0.2   # провал делает карточку труднее, а не легче
repetition['easiness_factor'] = max(repetition['easiness_factor'], 1.3)
```

---

### B06. Интервал повторения не растёт геометрически

**Где:** `data_level.py:256-258`

**Суть.** Для `repetition_number >= 2` интервал всегда вычисляется как `6 * easiness_factor` дней.
В SM-2 он должен быть `I(n) = I(n-1) * EF`, то есть накапливаться. `repetition_number` при этом
растёт, но на интервал не влияет — алгоритм вырождается в «~15–32 дня навсегда».

**Воспроизведение:**

```
iteration 1: repetition_number=1 EF=2.600 interval=1d
iteration 2: repetition_number=2 EF=2.700 interval=6d
iteration 3: repetition_number=3 EF=2.800 interval=16d
iteration 4: repetition_number=4 EF=2.900 interval=16d
iteration 5: repetition_number=5 EF=3.000 interval=17d
iteration 6: repetition_number=6 EF=3.100 interval=17d

after 30 perfect answers: EF = 5.50, repetition_number = 33, interval = 32 days
```

По SM-2 последовательность была бы 1 → 6 → 16 → 42 → 118 → 342 дня (при том же росте EF);
здесь она упирается в линейный рост `6 * EF`. Для хорошо выученной фразы интервал в 32 дня
вместо нескольких месяцев — существенное искажение методики, ради которой приложение написано.

**Как исправить.** Хранить текущий интервал и умножать его:

```python
if repetition['repetition_number'] == 0:
    days = 1
elif repetition['repetition_number'] == 1:
    days = 6
else:
    days = repetition.get('interval', 6) * repetition['easiness_factor']
repetition['interval'] = days
repetition['time_to_repeat'] = (datetime.now() + timedelta(days=days)).strftime(datetime_format)
```

---

### B07. Проваленная карточка блокирует выдачу всех новых фраз

**Где:** `data_level.py:260-261` (`_supermemo2`, ветка провала) + `data_level.py:103-106` (`determine_next_phrase`)

**Суть.** При неправильном ответе `time_to_repeat` **не изменяется** — карточка остаётся просроченной.
`determine_next_phrase()` устроена так, что новая (неначатая) фраза выдаётся только когда
ни одна начатая не просрочена:

```python
if min_time_to_repeat_started_phrases <= datetime.now() or recommended_continuing_phrase == '':
    return recommended_started_phrase      # просроченная карточка всегда выигрывает
```

Значит, одна «трудная» карточка, которую пользователь не может ввести точно, **бессрочно блокирует
остальные фразы**: ни одна новая фраза не будет показана, пока она не сдана.
В сочетании с B08 (акценты) это практически гарантированный сценарий.

**Воспроизведение** (сквозной прогон приложения, словарь 70 фраз):

```
# 1-й запуск
Enter phrase "What is it?" in Spanish:  -> Correct!
Enter phrase "It is" in Spanish:        -> Not bad. Right answer is: Lo es   (e,s — красные)
Enter phrase "It is" in Spanish:        <- ТА ЖЕ карточка сразу снова

# 2-й запуск: 68 фраз ещё не начаты, но показана снова только она
No new phrases
Enter phrase "It is" in Spanish:
```

```
# стенд, проверка планировщика
time_to_repeat = 2026.09.08 17:17:26 | already due: True
next phrase chosen: 'It is'
```

**Как исправить.** При провале назначать короткий интервал, а не оставлять старую дату,
и/или ограничивать число подряд идущих повторов одной карточки:

```python
else:  # Incorrect response
    repetition['repetition_number'] = 0
    repetition['time_to_repeat'] = (datetime.now() + timedelta(minutes=10)).strftime(datetime_format)
```

Либо чередовать: после `N` показов одной карточки выдавать новую, а к проваленной возвращаться
в конце сессии.

---

### B08. Диакритика не нормализуется — правильный ответ без акцентов наказывается

**Где:** `data_level.py:186-188` (`_compact`), `data_level.py:171-177`

**Суть.** `_compact()` оставляет только `isalnum()` и пробел, но `é`, `í`, `á`, `ñ` являются
буквенными символами, поэтому **сохраняются**. Пользователь без испанской раскладки физически
не может получить «Correct!» для большинства фраз: один пропущенный акцент обрушивает
`jaro_similarity` ниже порога `level_good = 0.97`.

**Воспроизведение:**

```
'que es'    vs 'Qué es?'   : jaro=0.8222 -> Not bad
'si'        vs 'Sí'        : jaro=0.6667 -> Not bad
'aqui esta' vs 'Aquí está' : jaro=0.8519 -> Not bad
'yo no se'  vs 'Yo no sé'  : jaro=0.9167 -> Not bad
'asi es'    vs 'Así es'    : jaro=0.8889 -> Not bad
'como yo'   vs 'Como yo'   : jaro=1.0000 -> Correct!
thresholds: excellent=0.99 good=0.97 mediocre=0.65
```

Обратите внимание на `'si'` против `'Sí'` — **0.67**, это граница вердикта «Wrong».
Акценты содержатся в подавляющем большинстве переводов текущего словаря, то есть проблема
системная, а не краевая. Тот же дефект усиливает B11: акцентированные буквы помечаются красным
как ошибки — `find_user_mistakes('Que es, senor?', '¿Qué es, señor?')` вернул
`[True, False, False, False, True, ..., False, False, False, True]`.

**Как исправить.** Складывать акценты перед сравнением:

```python
import unicodedata

@staticmethod
def _fold_accents(s: str) -> str:
    return ''.join(ch for ch in unicodedata.normalize('NFD', s)
                   if not unicodedata.combining(ch))

@staticmethod
def _compact(input_string: str) -> str:
    input_string = DataOperations._fold_accents(input_string)
    return ''.join(ch for ch in input_string if ch.isalnum() or ch == ' ')
```

Свёртку применять **только к сравнению**; показывать пользователю эталон с акцентами.
Альтернатива — `jellyfish.jaro_winkler_similarity` после той же нормализации.

---

### B09. `EOFError` из `input()` не обрабатывается

**Где:** `ui_level.py:15`, `flywheel.py:36-55`

**Суть.** `flywheel.py` перехватывает только `KeyboardInterrupt`. При закрытом или исчерпанном stdin
(перенаправление ввода, `Ctrl+Z` в Windows, `Ctrl+D` в POSIX) `input()` бросает `EOFError`,
который ничем не перехвачен.

**Воспроизведение:**

```
Enter phrase "I know" in Spanish:
  EOFError out of user_session -> EOFError('EOF when reading a line')
```

Последствие: traceback на экран и аварийное завершение **без финального сохранения** —
строки `flywheel.py:59-60` не выполняются, то есть ответы текущей сессии теряются.

**Как исправить.** Обработать `EOFError` наравне с `KeyboardInterrupt`:

```python
except (KeyboardInterrupt, EOFError):
    pass  # ввод завершён — выходим вежливо, данные сохраняются ниже
```

Либо перехватывать в `user_session()` и возвращать `None, ''` (трактуя как команду `/exit`).

---

## 🟡 Средняя серьёзность

### B10. Неправильный пробел в первой/последней позиции эталона исчезает из вывода

**Где:** `ui_level.py:44-55` (`_print_colored_diff`)

**Суть.** Для пробела, помеченного как ошибка, есть две ветки: если у него есть оба соседа —
печатается `_` или пробел; если пробел **первый или последний** — не печатается **ничего**.
В результате показанный «правильный ответ» оказывается короче настоящего, и пользователь
видит искажённую фразу.

**Воспроизведение** (прямой вызов функции, экранирующие коды показаны как есть):

```
reference='ab ' correction=[False, False, False]
  printed='\x1b[31ma\x1b[31mb'          <- напечатано 'ab', конечный пробел исчез
reference=' a'  correction=[False, False]
  printed='\x1b[31ma'                    <- начальный пробел исчез
reference='a b' correction=[True, False, True]
  printed='\x1b[32ma\x1b[31m_\x1b[32mb'  <- здесь пробел подсвечен как '_' (ветка работает)
reference=' a ' correction=[False, True, False]
  printed='\x1b[32ma'                    <- ОБА крайних пробела исчезли: из ' a ' осталось 'a'
```

**Достижимость.** В текущем конвейере данные проходят `str.strip()` (`system_level.py:37, 64`),
поэтому эталон с крайними пробелами может появиться только из отредактированного вручную
`repetitions.json` или при изменении источника фраз. Дефект **латентный**, но это ровно тот случай,
когда функция молча теряет символ: исправить дешевле, чем искать потом.

**Как исправить.** Убрать особое ветвление и печатать пробел всегда:

```python
for i, ch in enumerate(reference):
    if correction[i]:
        print(Fore.GREEN + ch, end='')
    elif ch == ' ':
        between_correct = 0 < i < len(reference) - 1 and correction[i - 1] and correction[i + 1]
        print(Fore.RED + ('_' if between_correct else ' '), end='')
    else:
        print(Fore.RED + ch, end='')
```

---

### B11. Порог `n >= 3` искажает разбор ошибок в обе стороны

**Где:** `data_level.py:219-222` (`find_user_mistakes`)

**Суть.** Группы совпадающих символов короче трёх помечаются как ошибки — «чтобы не показывать
слишком короткие группы правильных букв». На коротких фразах это даёт два противоположных
по видимому эффекту искажения.

**Воспроизведение на реальных фразах из `phrases.txt`:**

```
user='Yo'     ref='Y yo'    jaro=0.5833 -> correction_map=[False, False, False, False]
    помечено как ошибки: 4/4   <-- ВЕСЬ ответ красный
user='es'     ref='Eso es'  jaro=0.7778 -> correction_map=[False, False, False, False, False, False]
    помечено как ошибки: 6/6   <-- ВЕСЬ ответ красный
user='Lo está' ref='Lo es'  jaro=0.9048 -> correction_map=[True, True, True, True, True]
    помечено как ошибки: 0/5   <-- вердикт «Not bad», но эталон показан ЦЕЛИКОМ ЗЕЛЁНЫМ
```

1. **Правильные буквы показаны как ошибки.** Пользователь, набравший `Yo` вместо `Y yo`, видит
   «Not bad. Right answer is: **Y yo**» — и весь эталон красный, хотя две буквы из четырёх он угадал.
   Причина: единственный совпавший блок короче трёх символов и отброшен порогом.
2. **Ошибки не показаны вовсе.** Для `Lo está` против `Lo es` блок `lo es` (5 символов) совпал,
   поэтому эталон рисуется полностью зелёным: пользователь получает оценку 0.90 («Not bad»),
   но **не видит, что именно у него неверно**. Лишние символы ввода (`tá`) в разбор не попадают,
   потому что `correction_map` строится по эталону, а не по вводу.

**Как исправить.** Завязать порог на длину эталона и дополнить разбор символами ввода,
которых нет в эталоне:

```python
threshold = 3 if len(minified_reference) >= 6 else 1     # для коротких фраз принимаем и 1 символ
...
if n >= threshold:
```

И выводить не только «что верно в эталоне», но и «что лишнего во вводе» — например,
после цветного эталона печатать лишние символы пользователя красным.

---

### B12. `SequenceMatcher(isjunk=...)` — мёртвый код, а стороны сравнения нормализованы по-разному

**Где:** `data_level.py:199-216`

**Суть.** Два связанных недостатка:

1. **`isjunk` не может сработать.** В `difflib.SequenceMatcher` функция `isjunk` применяется
   только ко **второй** последовательности (`b`). Здесь `b = minified_reference`, который построен
   фильтром `ch.isalnum() or ch == ' '` — «мусорных» символов в нём нет по построению:
   ```
   isjunk is applied to the SECOND sequence (b = minified_reference) only;
     minified_reference='Que es Hola' -> junk chars in it: []  (always empty)
   ```
   Аргумент вводит читателя в заблуждение: кажется, что пунктуация игнорируется, но это не так.

2. **Стороны нормализованы несогласованно.** Ввод проходит `_cleanup_user_input()`
   (пунктуация из белого списка **сохраняется**), а эталон — «минификацию» (пунктуация **удаляется**).
   В отличие от `find_max_string_similarity()`, где обе стороны прогоняются через `_compact()`,
   здесь `_compact()` к вводу не применяется:
   ```
   _cleanup_user_input('Lo, es')  -> 'lo, es'      (запятая осталась)
   minified reference 'Lo es'     -> 'lo es'       (без пунктуации)
   ```

**Последствия (реальные фразы из словаря):**

```
user='Lo, es'  ref='Lo es'          jaro=1.0000 -> correction_map=[False, False, True, True, True]
   похожесть 100 %, но разбор помечает 2 символа эталона как ошибки
user='Que es, senor?' ref='¿Qué es, señor?'      -> correction_map=[True, False, False, False, True, ...]
   одна лишняя запятая во вводе помечает как ошибки ПРОБЕЛ и следующие за ним буквы
```

Первая строка показывает расхождение двух путей сравнения: оценка (`_compact` + jaro) и разбор
(«минификация» только эталона) нормализуют вход по-разному, поэтому могут противоречить друг другу.

**Как исправить.** Привести обе стороны к одному виду и убрать бесполезный `isjunk`:

```python
user_input = DataOperations._compact(DataOperations._cleanup_user_input(user_input).lower())
reference = DataOperations._compact(reference.lower())
seq = SequenceMatcher(None, user_input, reference)
```

Индексы совпадений при этом останутся согласованными с `transformation_matrix`, которая строится
по тому же правилу фильтрации.

---

### B13. Первый запуск встречает пользователя двумя сообщениями об ошибке разбора

**Где:** `system_level.py:24-26` (создание пустого файла), `system_level.py:83-94` (чтение JSON)

**Суть.** `find_or_create_file()` создаёт пустые `repetitions.json` и `user_statistics.txt`,
а `read_json_from_file()` немедленно пытается их разобрать и печатает `JSONDecodeError`.
Сообщение выглядит как авария, хотя это штатный первый запуск. Хуже то, что оно **идентично**
сообщению о реально повреждённом файле (B01) — пользователь не может отличить норму от беды.

**Воспроизведение** (чистый каталог, первый запуск приложения, ввод сразу закрыт):

```
Cannot open or parse repetitions.json file: JSONDecodeError('Expecting value: line 1 column 1 (char 0)')
Cannot open or parse user_statistics.txt file: JSONDecodeError('Expecting value: line 1 column 1 (char 0)')
Added 70 new phrases
Type "/exit" or press Ctrl+C to quit
```

**Как исправить.** Пустой файл — не ошибка разбора:

```python
if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
    return {}, True            # файл только что создан — данных ещё нет
```

Это совмещается с исправлением B01, где `False` означает «файл существует, но не читается».

---

### B14. Файлы данных создаются в CWD, а словарь ищется у приложения — асимметрия путей

**Где:** `system_level.py:15` (проверка относительно CWD), `system_level.py:24` (создание в CWD),
`system_level.py:19-21` (поиск обходом дерева)

**Суть.** Логика поиска неоднородна: если файла нет в текущем каталоге, он ищется обходом дерева,
а **создаётся всегда в текущем каталоге**. Поэтому при запуске не из каталога приложения
`phrases.txt` находится рядом с программой, а `repetitions.json` и `user_statistics.txt`
появляются в месте запуска. История обучения «привязывается» к каталогу, из которого
пользователь однажды стартовал.

**Воспроизведение** (приложение в `firstrun2\deep\Code`, запуск из `firstrun2`):

```
--- где оказались файлы данных ---
...\firstrun2\deep\Code\phrases.txt        <- словарь найден обходом рядом с приложением
...\firstrun2\repetitions.json             <- создан в CWD
...\firstrun2\user_statistics.txt          <- создан в CWD
```

Обратный эффект того же дефекта: следующий запуск уже **из** `deep\Code` не нашёл
`repetitions.json` в CWD, но подобрал его обходом из родительского каталога:

```
CWD = ...\firstrun2\deep\Code, файла repetitions.json здесь нет
No new phrases          <- подхвачен ...\firstrun2\repetitions.json, созданный прошлым запуском
```

То есть место хранения истории меняется от запуска к запуску в зависимости от CWD, а в связке
с B04 возможно и подключение совсем постороннего файла.

**Как исправить.** Единый каталог данных, не зависящий от CWD:

```python
DATA_DIR = Path(__file__).resolve().parent          # или %APPDATA%/flywheel для переносимости

@staticmethod
def data_file_path(filename: str) -> str:
    path = DATA_DIR / filename
    if not path.exists():
        path.touch()
    return str(path)
```

Если поддержка «своего» словаря пользователя нужна — искать его в явном порядке
(CWD → каталог приложения → `%APPDATA%`) и **печатать выбранный путь** при старте.

---

### B15. Структура записей `repetitions.json` не валидируется — `KeyError`, `ValueError`, `TypeError`

**Где:** `data_level.py:62` (`repetitions[native_part]['translations']`),
`data_level.py:92-98` (`value['attempts']`, `strptime`), `data_level.py:112-117`, `data_level.py:249-265`

**Суть.** Код обращается к полям записи по ключам и парсит дату без каких-либо проверок.
Файл `repetitions.json` лежит рядом с приложением и предназначен для ручного просмотра,
поэтому опечатка пользователя, слияние двух файлов или запись более старой версией программы
приводят к немедленному падению — причём **после** того, как `merge()` уже изменил данные в памяти.

**Воспроизведение** (одна запись, испорченная разными способами):

```
a valid record                     | determine_next_phrase -> 'It is' | update_repetitions -> OK
"attempts" key is missing          | determine_next_phrase -> KeyError: 'attempts'
"time_to_repeat" key is missing    | determine_next_phrase -> KeyError: 'time_to_repeat'
"easiness_factor" key is missing   | determine_next_phrase -> 'It is' | update_repetitions -> KeyError: 'easiness_factor'
time_to_repeat = "01/01/2020"      | determine_next_phrase -> ValueError: time data '01/01/2020' does not match format '%Y.%m.%d %H:%M:%S'
time_to_repeat = null              | determine_next_phrase -> TypeError: strptime() argument 1 must be str, not None
time_to_repeat = "2020.13.45 ..."  | determine_next_phrase -> ValueError: time data '2020.13.45 99:99:99' does not match format
easiness_factor = "2.5" (string)   | update_repetitions -> TypeError: can only concatenate str (not "float") to str
repetition_number = "1" (string)   | update_repetitions -> TypeError: can only concatenate str (not "int") to str
attempts = {} (dict, not list)     | update_repetitions -> AttributeError: 'dict' object has no attribute 'append'
the whole record is a string       | determine_next_phrase -> TypeError: string indices must be integers, not 'str'
the whole record is a list         | determine_next_phrase -> TypeError: list indices must be integers or slices, not str
```

Ни один из случаев не обрабатывается: пользователь получает traceback вместо сообщения
«запись X повреждена, пересоздаю её».

**Как исправить.** Проверять и чинить запись при загрузке:

```python
REQUIRED = {'translations': (str, list), 'time_to_repeat': str,
            'easiness_factor': (int, float), 'repetition_number': int, 'attempts': list}

@staticmethod
def sanitize_repetition(rep) -> dict | None:
    """Возвращает исправленную запись или None, если её нужно пересоздать."""
    if not isinstance(rep, dict):
        return None
    for key, types in DataOperations.REQUIRED.items():
        if not isinstance(rep.get(key), types):
            return None
    try:
        datetime.strptime(rep['time_to_repeat'], datetime_format)
    except ValueError:
        return None
    rep['attempts'] = [a for a in rep['attempts']
                       if isinstance(a, (list, tuple)) and len(a) == 2][-max_attempts_len:]
    rep['easiness_factor'] = float(rep['easiness_factor'])
    rep['repetition_number'] = int(rep['repetition_number'])
    return rep
```

В `merge()` для записей, не прошедших проверку, создавать новую карточку с предупреждением.

---

### B16. `user_statistics.txt` не проходит `data_assessment` → `TypeError` на первом же ответе

**Где:** `flywheel.py:22`, `data_level.py:120-153`

**Суть.** Для `phrases` и `repetitions` есть проверка `data_assessment()`, а третий файл —
`statistics` — читается тем же `read_json_from_file()` и попадает прямо в `update_statistics()`
без единой проверки. Файл называется `.txt`, хотя содержит JSON, то есть сам провоцирует ручное
редактирование. Любое содержимое, отличное от словаря, даёт необработанное исключение
**внутри цикла сессии** — после того, как пользователь уже начал отвечать.

**Воспроизведение:**

```
a JSON list                  -> TypeError: list indices must be integers or slices, not str
a JSON string                -> TypeError: 'str' object does not support item assignment
attempts_num is a string     -> TypeError: can only concatenate str (not "int") to str
word sets are strings        -> OK (set('abc') молча превращает строку в набор букв)
```

Последняя строка — отдельная проблема: испорченные `native_words`/`english_words` не падают,
а **тихо искажают** статистику (`'abc'` → `['a', 'b', 'c']`).

**Как исправить.** Проверять статистику так же, как остальные данные:

```python
statistics = fop.read_json_from_file(user_statistics_file_path)
if not isinstance(statistics, dict) or not all(
        isinstance(statistics[k], t) for k, t in
        (('attempts_num', int), ('native_words', list), ('english_words', list))
        if k in statistics):
    print(f'{user_statistics_file_path} is corrupted - statistics are restarted')
    statistics = {}
```

Заодно стоит переименовать файл в `user_statistics.json`: расширение `.txt` при JSON-содержимом
вводит в заблуждение и пользователя, и редакторы (подсветка, форматирование, валидация).

---

### B18. Языки перепутаны в именах: `english_words` содержит испанские слова

**Где:** `system_level.py:45` (`'English'`), `data_level.py:52` (`english_part`),
`data_level.py:141-151` (`english_words`), `ui_level.py:15` (`in Spanish`)

**Суть.** Правая часть строки `phrases.txt` везде называется «english», хотя фактически это
**испанский** текст: заголовок самого файла обещает `native phrase || english phrase`,
интерфейс спрашивает `Enter phrase "..." in Spanish`, а данные содержат `What is it? || Que es?`.
Имена переменных, параметры сообщений и ключи сохраняемой статистики наследуют эту путаницу.

**Воспроизведение** (реальный результат `update_statistics`):

```
native_words  = ['is', 'it', 'what']
english_words = ['es', 'que']   <-- испанские слова в поле "english"
```

Поле `english_words` сохраняется в `user_statistics.txt` и переживает перезапуски, то есть
искажение фиксируется в данных пользователя. Дополнительно пользователь видит сообщения
с неверным названием языка:

```
Warning. Empty English phrase variant(s) skipped: ...
Warning. Too long English phrase variant (312 symbols, limit is 300) skipped: ...
```

**Как исправить.** Переименовать в языково-нейтральные термины (правая часть — «перевод»):

```python
# system_level.py
translation_phrases = FileOperations._split_into_phrases(phrases_pair[1], 'translation', string)
# data_level.py
for native_part, translation_part in phrases.items():
# статистика
statistics['translation_words'] = ...      # вместо english_words
```

Если обратная совместимость со старым `user_statistics.txt` важна — читать оба ключа,
писать новый. Либо сделать язык настраиваемым (`target_language = 'Spanish'`) и подставлять
его в приглашение и предупреждения.

---

### B19. Сбой записи обрывает сессию молча, а сообщение об ошибке дублируется

**Где:** `flywheel.py:49-52`, `flywheel.py:59-60`, `system_level.py:130`

**Суть.** Когда `save_json_to_file()` возвращает `False`, цикл прерывается установкой
`save_failed = True`, но пользователю **не сообщается, что сессия остановлена именно из-за этого**.
Затем строки 59-60 повторяют ту же запись, и то же самое сообщение об ошибке печатается
второй раз. В итоге человек видит дубль низкоуровневой строки и не понимает, почему ввод
больше не запрашивается.

**Воспроизведение** (реальный запуск приложения; `user_statistics.txt` занят — здесь каталогом):

```
Cannot open or parse user_statistics.txt file: PermissionError(13, 'Permission denied')
No new phrases
Type "/exit" or press Ctrl+C to quit
Enter phrase "What is it?" in Spanish:
Wrong. Right answer is: Que es?
Cannot save user_statistics.txt file: PermissionError(13, 'Отказано в доступе')
Cannot save user_statistics.txt file: PermissionError(13, 'Отказано в доступе')   <-- ДУБЛЬ
Session finished, but user_statistics.txt WAS NOT saved. The file keeps the last successfully saved data, nothing was corrupted.
```

Команда `/exit`, переданная следом, даже не была прочитана: сессия оборвалась после первого ответа.
Обратите внимание и на смешение языков в выводе (`PermissionError(13, 'Отказано в доступе')` —
текст локали ОС внутри английского сообщения).

**Как исправить.** Сообщить причину сразу и не повторять заведомо провалившуюся запись:

```python
if not fop.save_json_to_file(repetitions_file_path, repetitions):
    save_failed = True
elif not fop.save_json_to_file(user_statistics_file_path, statistics):
    save_failed = True

if save_failed:
    print('Saving failed - the session is stopped to avoid losing your answers. '
          'Check that the data files are writable and restart the app.')
    break
```

А финальное сохранение (строки 59-60) выполнять только для тех файлов, которые не были
помечены как проваленные, — либо печатать итоговое сообщение один раз, без повтора
деталей исключения.

<!-- APPEND-HERE -->








