# Программное обеспечение для автоматизированной настройки терапии солидных опухолей

Программный комплекс для численного моделирования и автоматизированной настройки
комбинированной терапии солидных опухолей на основе реакционно-диффузионной
модели CAR-T терапии, химиотерапии и иммунотерапии. Python-приложение (PySide6)
обеспечивает интерфейс, визуализацию и автоматизацию расчётов, C++ ядро выполняет
численное решение системы дифференциальных уравнений в частных производных.

- Репозиторий: <https://github.com/<user>/<repo>>
- Версия, соответствующая отчёту: тег `v1.0`
- Поддерживаемые ОС: Windows 10/11, Linux, macOS

## Содержание

1. [Возможности](#возможности)
2. [Структура репозитория](#структура-репозитория)
3. [Требования](#требования)
4. [Установка зависимостей](#установка-зависимостей)
5. [Получение исходного кода](#получение-исходного-кода)
6. [Быстрый старт](#быстрый-старт)
7. [Пошаговая ручная установка](#пошаговая-ручная-установка)
8. [Проверка работоспособности](#проверка-работоспособности)
9. [Частые проблемы](#частые-проблемы)

## Возможности

- Численное решение системы уравнений в частных производных:
  конечно-разностная аппроксимация пространственных производных
  (центрально-разностная схема второго порядка точности) и интегрирование по времени.
- Реализованные численные методы: явный Эйлер, неявный Эйлер, метод Рунге — Кутты 4-го порядка.
- Соблюдение условия Куранта — Фридрихса — Леви (CFL) для устойчивости явной схемы.
- Параметрический анализ чувствительности модели (в т.ч. скорость роста опухоли `r_T`
  и коэффициент диффузии опухолевых клеток `D_T`).
- Идентификация параметров модели по экспериментальным данным (координатный спуск,
  минимизация функционала невязки).
- Интерактивная визуализация: 2D-карты, совмещённые карты `C + T`, срезы по `x` и `y`,
  динамика объёма опухоли, значения в центре домена, сравнение модели с экспериментом.
- Проведение серий расчётов и обучение модели без участия пользователя в промежуточных шагах.

## Структура репозитория

```text
<repo>/
├── main.py                  # точка входа GUI (PySide6)
├── requirements.txt         # Python-зависимости
├── modules/
│   └── solver/cpp/          # исходный код C++ ядра и CMakeLists.txt
├── bin/                     # собранные модули modeling_2d и grad_optim (создаётся при сборке)
├── build.sh / build.bat     # сборка C++ ядра (Linux/macOS / Windows)
└── run.sh / run.bat         # сборка при необходимости + запуск GUI
```

Каталоги `bin/`, `.venv/` и `modules/solver/cpp/build/` создаются автоматически
и в репозиторий не входят.

## Требования

| Компонент | Версия | Назначение |
|---|---|---|
| Python | 3.9 или новее | интерфейс, визуализация, автоматизация |
| CMake | 3.16 или новее | сборка C++ ядра |
| Компилятор C++17 | g++ 9+ / clang 10+ / MinGW-w64 (g++ 9+) | сборка C++ ядра |
| Git | любая | получение исходного кода |

Python-библиотеки (устанавливаются автоматически из `requirements.txt`):
`PySide6`, `pandas`, `matplotlib`, `numpy`.

Для работы нужно около 1 ГБ свободного места (основная часть занята PySide6)
и доступ в интернет при первой установке зависимостей.

## Установка зависимостей

### Windows

1. **Python.** Скачайте установщик с <https://www.python.org/downloads/>.
   При установке обязательно отметьте пункт **Add python.exe to PATH**.
2. **CMake.** Скачайте установщик с <https://cmake.org/download/> и выберите
   вариант **Add CMake to the system PATH for all users** (или для текущего пользователя).
3. **MinGW-w64 (g++).** Рекомендуемый способ — через MSYS2:
   1. Установите MSYS2 с <https://www.msys2.org/> (путь по умолчанию `C:\msys64`).
   2. Откройте терминал **MSYS2 UCRT64** и выполните:
      ```bash
      pacman -S --needed mingw-w64-ucrt-x86_64-gcc mingw-w64-ucrt-x86_64-make
      ```
   3. Добавьте `C:\msys64\ucrt64\bin` в переменную среды `Path`
      (Параметры → Система → О системе → Дополнительные параметры системы →
      Переменные среды).
4. **Git.** Скачайте с <https://git-scm.com/download/win>.
5. Откройте **новое** окно `cmd` или PowerShell и проверьте установку:
   ```bat
   python --version
   cmake --version
   g++ --version
   git --version
   ```
   Все четыре команды должны вывести версии. Если какая-то команда не найдена,
   проверьте переменную `Path` и перезапустите терминал.

### Linux (Debian / Ubuntu)

```bash
sudo apt update
sudo apt install -y git cmake g++ make python3 python3-venv python3-pip
```

Для PySide6 на «чистой» системе могут понадобиться системные библиотеки
Qt/OpenGL/XCB:

```bash
sudo apt install -y libgl1 libegl1 libxkbcommon-x11-0 libxcb-cursor0
```

Другие дистрибутивы: Fedora — `sudo dnf install git cmake gcc-c++ make python3`,
Arch — `sudo pacman -S git cmake gcc make python`.

Проверка:

```bash
python3 --version && cmake --version && g++ --version
```

### macOS

```bash
xcode-select --install          # компилятор clang и git
brew install cmake python
```

Проверка:

```bash
python3 --version && cmake --version && clang++ --version
```

## Получение исходного кода

```bash
git clone https://github.com/<user>/<repo>.git
cd <repo>
git checkout v1.0
```

Последняя команда переключает репозиторий на версию, для которой получены
результаты в отчёте.

## Быстрый старт

Скрипт запуска сам выполнит все необходимые действия: соберёт C++ ядро (если
оно ещё не собрано), создаст виртуальное окружение `.venv`, установит
Python-зависимости и запустит приложение.

**Windows** (из каталога репозитория):

```bat
run.bat
```

**Linux / macOS:**

```bash
chmod +x build.sh run.sh
./run.sh
```

Первый запуск занимает несколько минут (сборка и загрузка PySide6),
последующие — несколько секунд. После запуска откроется окно приложения.

Чтобы пересобрать C++ ядро после изменения исходников, запустите
`build.bat` (Windows) или `./build.sh` (Linux/macOS) и затем снова `run`.

## Пошаговая ручная установка

Этот вариант нужен, если скрипты по какой-то причине не подходят
или требуется понять, что именно они делают.

### 1. Сборка C++ ядра

Linux / macOS:

```bash
cmake -S modules/solver/cpp -B modules/solver/cpp/build -DCMAKE_BUILD_TYPE=Release
cmake --build modules/solver/cpp/build --target modeling_2d grad_optim -j 4
mkdir -p bin
cp modules/solver/cpp/build/modeling_2d modules/solver/cpp/build/grad_optim bin/
```

Windows (cmd):

```bat
cmake -S modules\solver\cpp -B modules\solver\cpp\build -G "MinGW Makefiles" -DCMAKE_BUILD_TYPE=Release
cmake --build modules\solver\cpp\build --target modeling_2d grad_optim
mkdir bin
copy modules\solver\cpp\build\modeling_2d.exe bin\
copy modules\solver\cpp\build\grad_optim.exe bin\
```

В результате в каталоге `bin/` должны появиться два исполняемых файла:
`modeling_2d` (решатель прямой задачи) и `grad_optim` (идентификация параметров).

### 2. Виртуальное окружение и Python-зависимости

Linux / macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Windows (cmd):

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

В PowerShell, если активация запрещена политикой выполнения, один раз выполните
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.

### 3. Запуск

```bash
python main.py
```

Команду нужно выполнять из корня репозитория при активированном `.venv`.

## Проверка работоспособности

1. После сборки в каталоге `bin/` есть `modeling_2d` и `grad_optim`
   (на Windows — с расширением `.exe`).
2. Команда `python -c "import PySide6, numpy, pandas, matplotlib; print('OK')"`
   выводит `OK`.
3. Запуск `run.bat` / `./run.sh` открывает главное окно приложения без
   сообщений об ошибках в консоли.

## Частые проблемы

**`cmake` / `g++` / `python` не найден.** Программа не установлена или не
добавлена в `Path`. Установите её по разделу «Установка зависимостей» и
откройте новое окно терминала.

**Windows: ошибка `CMake Error: ... does not match the generator used previously`.**
Каталог сборки был создан другим генератором. Удалите его и повторите сборку:

```bat
rmdir /s /q modules\solver\cpp\build
build.bat
```

**Windows: `CMake was unable to find a build program corresponding to "MinGW Makefiles"`.**
В `Path` нет `mingw32-make`. Установите пакет `mingw-w64-ucrt-x86_64-make`
через MSYS2 (см. выше) и проверьте, что `C:\msys64\ucrt64\bin` есть в `Path`.

**Windows: в консоли вместо русского текста нечитаемые символы.**
Скрипты переключают консоль в UTF-8 командой `chcp 65001`; если шрифт консоли
не поддерживает кириллицу, выберите шрифт Consolas или используйте Windows Terminal.

**Windows: после установки Python команда `python` открывает Microsoft Store.**
Отключите псевдонимы: Параметры → Приложения → Дополнительные параметры →
Псевдонимы выполнения приложений → выключите `python.exe` и `python3.exe`.

**Linux: `qt.qpa.plugin: Could not load the Qt platform plugin "xcb"`.**
Не хватает системных библиотек. Установите их командой из раздела
«Linux (Debian / Ubuntu)»; недостающую библиотеку называет сообщение
об ошибке, если запустить `QT_DEBUG_PLUGINS=1 python main.py`.

**Linux: `./run.sh: Permission denied`.** Выполните `chmod +x build.sh run.sh`
или запускайте через `bash run.sh`.

**macOS: нет команды `nproc`.** Сообщение безвредно: скрипт сборки использует
`sysctl -n hw.ncpu`.

**Ошибка при `pip install` из-за версии Python.** PySide6 требует Python 3.9+.
Проверьте `python --version` и при необходимости установите более новую версию.

**Приложение запускается, но расчёт не стартует.** Проверьте, что файлы
`modeling_2d` и `grad_optim` лежат в `bin/` и имеют право на исполнение
(`chmod +x bin/*` на Linux/macOS).
