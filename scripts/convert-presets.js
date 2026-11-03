#!/usr/bin/env node
/**
 * Fast conversion of Milkdrop .milk files to Butterchurn JSON format.
 * Skips heavy shader optimization - uses raw parsed output from milkdrop-preset-utils.
 * Butterchurn compiles EEL2 equations at runtime, so we just need the structure.
 */

const fs = require('fs');
const path = require('path');

const SRC_DIR = path.join(__dirname, '..', 'src', 'presets', 'cream-of-the-crop-raw');
const OUT_DIR = path.join(__dirname, '..', 'public', 'presets', 'cream-of-the-crop');

let milkdropPresetUtils;
function loadModules() {
  if (!milkdropPresetUtils) {
    milkdropPresetUtils = require('milkdrop-preset-utils');
  }
}

function convertSinglePreset(text) {
  const parsed = milkdropPresetUtils.splitPreset(text);

  const waves = (parsed.waves || []).map(wave => ({
    baseVals: wave.baseVals || {},
    init_eqs_str: wave.init_eqs_str || '',
    frame_eqs_str: wave.frame_eqs_str || '',
    point_eqs_str: wave.point_eqs_str || '',
  }));

  const shapes = (parsed.shapes || []).map(shape => ({
    baseVals: shape.baseVals || {},
    init_eqs_str: shape.init_eqs_str || '',
    frame_eqs_str: shape.frame_eqs_str || '',
  }));

  return {
    baseVals: parsed.baseVals || {},
    waves,
    shapes,
    init_eqs_str: parsed.presetInit || '',
    frame_eqs_str: parsed.perFrame || '',
    pixel_eqs_str: parsed.perVertex || '',
    warp: parsed.warp || '',
    comp: parsed.comp || '',
  };
}

function findMilkFiles(dir) {
  const files = [];
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  for (const entry of entries) {
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      files.push(...findMilkFiles(fullPath));
    } else if (entry.isFile() && entry.name.endsWith('.milk')) {
      files.push(fullPath);
    }
  }
  return files;
}

function scanCategories(dir) {
  const categories = {};
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  for (const entry of entries) {
    if (entry.isDirectory() && !entry.name.startsWith('.')) {
      const categoryPath = path.join(dir, entry.name);
      const milkFiles = findMilkFiles(categoryPath);
      if (milkFiles.length > 0) {
        categories[entry.name] = milkFiles;
      }
    }
  }
  return categories;
}

function sanitizePresetName(name) {
  return name.replace(/\.milk$/, '');
}

function main() {
  console.log('Loading converter modules...');
  loadModules();

  if (!fs.existsSync(SRC_DIR)) {
    console.error(`Source directory not found: ${SRC_DIR}`);
    console.error('Run scripts/download-presets.sh first.');
    process.exit(1);
  }

  if (!fs.existsSync(OUT_DIR)) {
    fs.mkdirSync(OUT_DIR, { recursive: true });
  }

  const categories = scanCategories(SRC_DIR);
  const categoryNames = Object.keys(categories).sort();

  let totalConverted = 0;
  let totalFailed = 0;
  const index = {};

  for (const catName of categoryNames) {
    const files = categories[catName];
    console.log(`${catName}: ${files.length} presets...`);

    const presets = {};
    const manifest = [];

    for (const filePath of files) {
      try {
        const text = fs.readFileSync(filePath, 'utf-8');
        if (!text.includes('[preset00]')) continue;

        const presetName = sanitizePresetName(path.basename(filePath));
        presets[presetName] = convertSinglePreset(text);
        manifest.push(presetName);
        totalConverted++;
      } catch (e) {
        totalFailed++;
      }
    }

    if (manifest.length > 0) {
      const outFile = path.join(OUT_DIR, `${catName}.json`);
      fs.writeFileSync(outFile, JSON.stringify({
        _category: catName,
        _count: manifest.length,
        _manifest: manifest,
        presets,
      }));
      index[catName] = { count: manifest.length, file: `${catName}.json` };
      console.log(`  -> ${manifest.length} presets`);
    }
  }

  fs.writeFileSync(path.join(OUT_DIR, '_index.json'), JSON.stringify(index, null, 2));

  console.log(`\nDone: ${totalConverted} converted, ${totalFailed} failed`);
  console.log(`Output: ${OUT_DIR}`);
}

main();
