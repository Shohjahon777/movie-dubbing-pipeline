/**
 * Configuration Module
 * Handles environment variables and directory management
 */

import dotenv from 'dotenv';
import { fileURLToPath } from 'url';
import { dirname, join, resolve } from 'path';
import { existsSync, mkdirSync } from 'fs';

// Load environment variables
dotenv.config();

// Get current directory (ES modules compatible)
const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const projectRoot = resolve(__dirname, '../..');

// Configuration
const config = {
  // API Configuration
  pythonApiUrl: process.env.PYTHON_API_URL || 'http://localhost:8000',
  apiPort: parseInt(process.env.API_PORT || '8000', 10),
  
  // Directory Paths
  inputDir: process.env.INPUT_DIR || join(projectRoot, 'data', 'input'),
  outputDir: process.env.OUTPUT_DIR || join(projectRoot, 'data', 'output'),
  tempDir: process.env.TEMP_DIR || join(projectRoot, 'data', 'temp'),
  modelDir: process.env.MODEL_CACHE_DIR || join(projectRoot, 'models'),
  
  // Language Configuration
  sourceLang: process.env.SOURCE_LANG || 'eng_Latn',
  targetLang: process.env.TARGET_LANG || 'uzb_Latn',
  
  // Processing Configuration
  maxAudioDuration: parseInt(process.env.MAX_AUDIO_DURATION || '3600', 10), // seconds
  referenceAudioDuration: parseInt(process.env.REFERENCE_AUDIO_DURATION || '10', 10), // seconds
  
  // Logging
  logLevel: process.env.LOG_LEVEL || 'INFO',
  
  // Project root
  projectRoot
};

/**
 * Ensure all required directories exist
 */
export function ensureDirectories() {
  const dirs = [
    config.inputDir,
    config.outputDir,
    config.tempDir,
    config.modelDir
  ];
  
  dirs.forEach(dir => {
    if (!existsSync(dir)) {
      mkdirSync(dir, { recursive: true });
      console.log(`Created directory: ${dir}`);
    }
  });
}

/**
 * Validate file exists
 */
export function validateFile(filePath) {
  if (!existsSync(filePath)) {
    throw new Error(`File not found: ${filePath}`);
  }
  return true;
}

/**
 * Validate file extension
 */
export function validateVideoFile(filePath) {
  const validExtensions = ['.mp4', '.avi', '.mov', '.mkv', '.webm'];
  const ext = filePath.toLowerCase().substring(filePath.lastIndexOf('.'));
  
  if (!validExtensions.includes(ext)) {
    throw new Error(`Invalid video file extension: ${ext}. Supported: ${validExtensions.join(', ')}`);
  }
  
  return true;
}

/**
 * Get API endpoint URL
 */
export function getApiUrl(endpoint) {
  const baseUrl = config.pythonApiUrl.replace(/\/$/, '');
  const path = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
  return `${baseUrl}${path}`;
}

export default config;
