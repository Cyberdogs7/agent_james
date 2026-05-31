@echo off
echo Starting Ada-V2...

:: Ensure virtual environment is used
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
)

:: Install Python Dependencies
echo Installing Python dependencies...
python -m pip install -r requirements.txt

:: Install Node Dependencies
echo Installing Node dependencies...
:: Prevent EPERM issues with Electron on Windows
:: Kill lingering electron processes to release file locks
taskkill /f /im electron.exe >nul 2>&1
call npx pnpm install --ignore-scripts

:: Ensure Electron binary is downloaded and correctly linked
call npx pnpm rebuild electron

:: Start the application
call npx pnpm run dev %*
