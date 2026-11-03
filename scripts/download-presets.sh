#!/bin/bash
# Download the Milkdrop Cream of the Crop presets
# Run this script once to populate the presets directory

set -e

PRESETS_DIR="src/presets/cream-of-the-crop-raw"
REPO_URL="https://github.com/projectM-visualizer/presets-cream-of-the-crop.git"

if [ -d "$PRESETS_DIR" ]; then
    echo "Presets directory already exists at $PRESETS_DIR"
    echo "To re-download, remove it first: rm -rf $PRESETS_DIR"
    exit 0
fi

echo "Downloading Cream of the Crop presets..."
git clone --depth 1 "$REPO_URL" "$PRESETS_DIR"

echo "Removing .git directory..."
rm -rf "$PRESETS_DIR/.git"

echo "Done! Presets downloaded to $PRESETS_DIR"
echo "Run 'node scripts/convert-presets.js' to convert them."
