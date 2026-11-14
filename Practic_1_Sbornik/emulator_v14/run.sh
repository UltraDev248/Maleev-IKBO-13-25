#!/usr/bin/env bash
set -e

# Автоопределение рабочей команды Python
if command -v python3 &>/dev/null && python3 -V &>/dev/null; then
    PY="python3"
elif command -v python &>/dev/null; then
    PY="python"
elif command -v py &>/dev/null; then
    PY="py"
else
    echo "Ошибка: интерпретатор Python не найден в системе."
    exit 1
fi

echo "[1/2] Запуск модульных тестов..."
$PY -m unittest discover -s tests

echo "[2/2] Запуск эмулятора со стартовым скриптом..."
$PY src/emulator.py --script tests/script_ok.txt