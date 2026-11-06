@echo off
setlocal
if not exist "%~dp0.venv\Scripts\pythonw.exe" (
    echo Falta el entorno virtual. Consulta docs\PYTHON.md para instalarlo.
    pause
    exit /b 1
)
start "" /d "%~dp0" "%~dp0.venv\Scripts\pythonw.exe" -m echosounder %*
