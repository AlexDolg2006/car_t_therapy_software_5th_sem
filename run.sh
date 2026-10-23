#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
ROOT="$(pwd)"
BIN_DIR="$ROOT/bin"
VENV_DIR="$ROOT/.venv"

if [ ! -f "$BIN_DIR/modeling_2d" ] || [ ! -f "$BIN_DIR/grad_optim" ]; then
    echo "=== Бинарники не найдены, запускаем сборку ==="
    bash "$ROOT/build.sh"
fi

PY="$(command -v python3 || command -v python || true)"
if [ -z "$PY" ]; then
    echo "Ошибка: Python 3.9+ не найден." >&2
    exit 1
fi

if [ ! -d "$VENV_DIR" ]; then
    echo "=== Создание виртуального окружения .venv ==="
    "$PY" -m venv "$VENV_DIR"
fi

echo "=== Проверка Python-зависимостей ==="
"$VENV_DIR/bin/python" -m pip install -q --upgrade pip
"$VENV_DIR/bin/python" -m pip install -q -r "$ROOT/requirements.txt"

echo "=== Запуск GUI ==="
exec "$VENV_DIR/bin/python" "$ROOT/main.py"