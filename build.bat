@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
set ROOT=%cd%
set SRC_DIR=%ROOT%\modules\solver\cpp
set BUILD_DIR=%SRC_DIR%\build

where cmake >nul 2>&1
if errorlevel 1 (
    echo Ошибка: cmake не найден в PATH. Установите CMake 3.16+ ^(см. README^).
    exit /b 1
)
where g++ >nul 2>&1
if errorlevel 1 (
    echo Ошибка: g++ не найден в PATH. Установите MinGW-w64 ^(см. README^).
    exit /b 1
)

echo === Сборка C++ ===
cmake -S "%SRC_DIR%" -B "%BUILD_DIR%" -G "MinGW Makefiles" -DCMAKE_BUILD_TYPE=Release || exit /b 1
cmake --build "%BUILD_DIR%" --target modeling_2d grad_optim || exit /b 1

if not exist "%ROOT%\bin" mkdir "%ROOT%\bin"
copy /Y "%BUILD_DIR%\modeling_2d.exe" "%ROOT%\bin\" >nul || exit /b 1
copy /Y "%BUILD_DIR%\grad_optim.exe"  "%ROOT%\bin\" >nul || exit /b 1

echo === Готово: бинарники в %ROOT%\bin ===
endlocal