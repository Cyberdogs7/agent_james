@echo off
echo Starting Ada-V2...

:: Install Python Dependencies
echo Installing Python dependencies...
python -m pip install -r requirements.txt

:: Install Node Dependencies
echo Installing Node dependencies...
:: Prevent EPERM issues with Electron on Windows during pnpm install
if exist "node_modules\electron" rmdir /s /q "node_modules\electron"
if exist "node_modules\.ignored_electron" rmdir /s /q "node_modules\.ignored_electron"
npx pnpm install

:: Start the application
npx pnpm run dev %*
