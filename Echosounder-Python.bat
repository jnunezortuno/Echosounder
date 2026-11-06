@echo off
setlocal
set "PYTHON=%~dp0.venv\Scripts\python.exe"
set "PYTHONW=%~dp0.venv\Scripts\pythonw.exe"
if not exist "%PYTHON%" (
    echo Falta el entorno virtual. Consulta docs\PYTHON.md para instalarlo.
    pause
    exit /b 1
)
if not exist "%PYTHONW%" (
    echo No se encuentra pythonw.exe en .venv\Scripts.
    pause
    exit /b 1
)
"%PYTHON%" -c "import echosounder.gui"
if errorlevel 1 (
    echo No se pudo cargar la aplicacion. Revisa el error anterior y docs\PYTHON.md.
    pause
    exit /b 1
)
start "" /d "%~dp0" "%PYTHONW%" -m echosounder %*
