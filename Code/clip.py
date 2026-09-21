# Напиши программу на Python, которая обрабатывает текстовый файл (название файла задано прямо в коде) и делает следующее:
# если строка пустая - удалить;
# если строка начинается с "#" - удалить;
# если строка содержит символы "||" - удалить все символы, начиная с "||".

# Получившийся текст должен быть записан в другой текстовый файл, с названием, как у входного текстового файла + "_clip", расширение такое же.

import os

# Название входного файла (задаётся здесь)
input_filename = "phrases.txt"

# Формируем название выходного файла
name, ext = os.path.splitext(input_filename)
output_filename = f"{name}_clip{ext}"

# Читаем и обрабатываем файл
with open(input_filename, 'r', encoding='utf-8') as infile:
    lines = infile.readlines()

processed_lines = []

for line in lines:
    # Убираем символ переноса строки для удобства обработки
    stripped = line.rstrip('\n').rstrip('\r')

    # Если строка пустая - пропускаем
    if stripped == "":
        continue

    # Если строка начинается с "#" - пропускаем
    if stripped.startswith("#"):
        continue

    # Если строка содержит "||" - удаляем всё начиная с "||"
    if "||" in stripped:
        stripped = stripped[:stripped.index("||")]

    # После обрезки по "||" строка могла стать пустой - проверяем
    if stripped == "":
        continue

    processed_lines.append(stripped)

# Записываем результат в выходной файл
with open(output_filename, 'w', encoding='utf-8') as outfile:
    outfile.write('\n'.join(processed_lines) + '\n')

print(f"Обработка завершена.")
print(f"Входной файл:  {input_filename}")
print(f"Выходной файл: {output_filename}")
print(f"Строк в результате: {len(processed_lines)}")
