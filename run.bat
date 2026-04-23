@echo off
echo Starting Ada-V2...

:: Install Python Dependencies
echo Installing Python dependencies...
python -m pip install -r requirements.txt

:: Install Node Dependencies
echo Installing Node dependencies...
npx pnpm install

:: Start the application
npx pnpm run dev %*
