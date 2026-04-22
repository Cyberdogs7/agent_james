#!/bin/bash
echo "Starting Ada-V2..."

# Install Python Dependencies
echo "Installing Python dependencies..."
python3 -m pip install -r requirements.txt

# Install Node Dependencies
echo "Installing Node dependencies..."
pnpm install

# Start the application
npm run dev "$@"
