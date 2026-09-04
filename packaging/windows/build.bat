@echo off
REM Build Halberd BAS Windows executable
REM Requires: Python 3.10+, pip install pyinstaller

echo Building Halberd BAS for Windows...

cd /d "%~dp0\..\.."

pip install -e ".[server]"
pip install pyinstaller

pyinstaller packaging\windows\halberd.spec --distpath packaging\windows\dist --workpath packaging\windows\build

echo.
echo Build complete: packaging\windows\dist\halberd.exe
echo.
pause
