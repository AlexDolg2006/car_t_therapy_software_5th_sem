@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
set ROOT=%cd%
set VENV_PY=%ROOT%\.venv\Scripts\python.exe

if not exist "%ROOT%\bin\modeling_2d.exe" goto build
if not exist "%ROOT%\bin\grad_optim.exe" goto build
goto venv

:build
echo === Бинарники не найдены, запускаем сборку ===
call "%ROOT%\build.bat"
if errorlevel 1 goto fail

:venv
if exist "%VENV_PY%" goto deps
echo === Создание виртуального окружения .venv ===
where py >nul 2>&1
if not errorlevel 1 (
    py -3 -m venv "%ROOT%\.venv"
) else (
    python -m venv "%ROOT%\.venv"
)
if errorlevel 1 goto fail

:deps
echo === Проверка Python-зависимостей ===
"%VENV_PY%" -m pip install -q --upgrade pip
"%VENV_PY%" -m pip install -q -r "%ROOT%\requirements.txt"
if errorlevel 1 goto fail

echo === Запуск GUI ===
"%VENV_PY%" "%ROOT%\main.py"
if errorlevel 1 goto fail
endlocal
exit /b 0

:fail
echo.
echo Запуск завершился с ошибкой. См. сообщения выше и раздел "Частые проблемы" в README.
pause
endlocal
exit /b 1