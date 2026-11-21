@echo off
setlocal
cd /d "%~dp0"
title Misora Editor: Unity3D Revision Tool ^& Story Editor

rem -- Preferred: Python 3.12 via Windows Python Launcher --
py -3.12 -c "import sys" >nul 2>&1
if not errorlevel 1 (
    py -3.12 "%~dp0misora.py" %*
    goto :check_error
)

rem -- Search other installed versions --
for %%V in (3.13 3.11 3.14) do (
    py -%%V -c "import sys" >nul 2>&1
    if not errorlevel 1 (
        py -%%V "%~dp0misora.py" %*
        goto :check_error
    )
)

rem -- Fallback: python on PATH --
where python >nul 2>&1
if not errorlevel 1 (
    python "%~dp0misora.py" %*
    goto :check_error
)

rem -- Fallback: generic py -3 --
where py >nul 2>&1
if not errorlevel 1 (
    py -3 "%~dp0misora.py" %*
    goto :check_error
)

echo [ERROR] Python not found on PATH.
echo Please run: py -3.12 -m pip install -r requirements.txt
pause
goto :end

:check_error
if errorlevel 1 (
    echo.
    echo [ERROR] Misora exited with error code %ERRORLEVEL%.
    pause
)

:end
endlocal
