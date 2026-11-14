#!/usr/bin/env bash

# Переход в корневую папку проекта, где лежит скрипт
cd "$(dirname "$0")" || exit 1

# Пауза перед закрытием окна при ЛЮБОМ завершении (успех или ошибка)
trap 'echo ""; read -r -p "Нажмите Enter для выхода..."' EXIT

if command -v python3 &>/dev/null && python3 -V &>/dev/null; then
    PY="python3"
elif command -v python &>/dev/null; then
    PY="python"
elif command -v py &>/dev/null; then
    PY="py"
else
    echo "Ошибка: интерпретатор Python не найден."
    exit 1
fi

echo "[1/3] Запуск пакета модульных тестов..."
$PY -m unittest discover -s tests || exit 1

echo "[2/3] Демонстрация на тестовом репозитории..."
$PY src/visualizer.py config_test.ini || exit 1

echo "[3/3] Запуск визуализатора на реальном NuGet пакете..."
$PY src/visualizer.py config.ini || exit 1

echo "Скрипт успешно выполнен."