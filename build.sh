#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
ROOT="$(pwd)"
SRC_DIR="$ROOT/modules/solver/cpp"
BUILD_DIR="$SRC_DIR/build"
BIN_DIR="$ROOT/bin"

if ! command -v cmake >/dev/null 2>&1; then
    echo "Ошибка: cmake не найден. Установите CMake 3.16+ (см. README)." >&2
    exit 1
fi
if ! command -v g++ >/dev/null 2>&1 && ! command -v clang++ >/dev/null 2>&1; then
    echo "Ошибка: не найден компилятор C++ (g++ или clang++)." >&2
    exit 1
fi

JOBS="$(nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 2)"

echo "=== Сборка C++ ==="
cmake -S "$SRC_DIR" -B "$BUILD_DIR" -DCMAKE_BUILD_TYPE=Release
cmake --build "$BUILD_DIR" --target modeling_2d grad_optim -j "$JOBS"

mkdir -p "$BIN_DIR"
cp "$BUILD_DIR/modeling_2d" "$BUILD_DIR/grad_optim" "$BIN_DIR/"
echo "=== Готово: бинарники в $BIN_DIR ==="