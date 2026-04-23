#!/bin/bash
echo "Starting Ada-V2..."

# Install Python Dependencies
echo "Installing Python dependencies..."
python3 -m pip install -r requirements.txt

# Install Node Dependencies
echo "Installing Node dependencies..."
npx pnpm install

# Ensure Electron binary is downloaded and correctly linked
npx pnpm rebuild electron

# Start the application
npx pnpm run dev "$@"
