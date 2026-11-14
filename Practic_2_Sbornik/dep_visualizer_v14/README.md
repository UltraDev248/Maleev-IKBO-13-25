# Visualizer of Dependencies (Variant 14 - NuGet)

Инструмент визуализации графа зависимостей для пакетов .NET (NuGet) без использования внешних библиотек.

## 1. Общее описание
Приложение извлекает прямые и транзитивные зависимости пакета, находит циклы, определяет порядок загрузки и формирует граф в форматах Mermaid, SVG и ASCII-дерева.

## 2. Настройки (config.ini)
- `package_name`: имя пакета.
- `package_version`: версия пакета.
- `repo_url`: URL API NuGet flat container или путь к файлу графа.
- `test_mode`: флаг тестового режима (`true`/`false`).
- `output_image`: имя сохраняемого SVG-файла.
- `ascii_tree`: включение вывода ASCII-дерева (`true`/`false`).

## 3. Команды сборки и запуска
```bash
# Запуск тестов
python -m unittest discover -s tests

# Запуск приложения
python src/visualizer.py config.ini

# Единый скрипт проверки
./run.sh