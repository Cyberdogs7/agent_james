@echo off
echo Starting Ada-V2...

:: Install Python Dependencies
echo Installing Python dependencies...
python -m pip install -r requirements.txt

:: Install Node Dependencies
echo Installing Node dependencies...
:: Prevent EPERM issues with Electron on Windows during pnpm install
:: Kill lingering electron processes to release file locks
taskkill /f /im electron.exe >nul 2>&1
if exist "node_modules\electron" rmdir /s /q "node_modules\electron"
if exist "node_modules\.ignored_electron" rmdir /s /q "node_modules\.ignored_electron"
call npx pnpm install

:: Ensure Electron binary is downloaded and correctly linked
call npx pnpm rebuild electron

:: Start the application
call npx pnpm run dev %*
