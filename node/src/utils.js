/**
 * Utility Functions
 * File management, path handling, and validation helpers
 */

import { existsSync, mkdirSync, unlinkSync, readdirSync, statSync } from 'fs';
import { join, dirname, basename, extname } from 'path';
import { promisify } from 'util';
import ffmpeg from 'fluent-ffmpeg';

/**
 * Create directory if it doesn't exist
 */
export function ensureDir(dirPath) {
  if (!existsSync(dirPath)) {
    mkdirSync(dirPath, { recursive: true });
  }
}

/**
 * Get file extension
 */
export function getFileExtension(filePath) {
  return extname(filePath).toLowerCase();
}

/**
 * Get filename without extension
 */
export function getFilenameWithoutExt(filePath) {
  return basename(filePath, extname(filePath));
}

/**
 * Generate unique temp file path
 */
export function getTempFilePath(prefix = 'temp', extension = '.tmp') {
  const timestamp = Date.now();
  const random = Math.random().toString(36).substring(2, 9);
  return join(process.env.TEMP_DIR || './data/temp', `${prefix}_${timestamp}_${random}${extension}`);
}

/**
 * Clean up temp files
 */
export function cleanupTempFiles(tempDir, pattern = null) {
  try {
    if (!existsSync(tempDir)) {
      return;
    }
    
    const files = readdirSync(tempDir);
    let deleted = 0;
    
    files.forEach(file => {
      const filePath = join(tempDir, file);
      const stats = statSync(filePath);
      
      if (stats.isFile()) {
        if (!pattern || file.includes(pattern)) {
          try {
            unlinkSync(filePath);
            deleted++;
          } catch (err) {
            console.warn(`Failed to delete temp file: ${filePath}`, err.message);
          }
        }
      }
    });
    
    if (deleted > 0) {
      console.log(`Cleaned up ${deleted} temp file(s)`);
    }
  } catch (err) {
    console.warn(`Error cleaning up temp files: ${err.message}`);
  }
}

/**
 * Get video duration using ffmpeg
 */
export function getVideoDuration(videoPath) {
  return new Promise((resolve, reject) => {
    ffmpeg.ffprobe(videoPath, (err, metadata) => {
      if (err) {
        reject(new Error(`Failed to get video duration: ${err.message}`));
        return;
      }
      
      const duration = metadata.format.duration;
      resolve(duration || 0);
    });
  });
}

/**
 * Get audio duration using ffmpeg
 */
export function getAudioDuration(audioPath) {
  return new Promise((resolve, reject) => {
    ffmpeg.ffprobe(audioPath, (err, metadata) => {
      if (err) {
        reject(new Error(`Failed to get audio duration: ${err.message}`));
        return;
      }
      
      const duration = metadata.format.duration;
      resolve(duration || 0);
    });
  });
}

/**
 * Format duration in seconds to HH:MM:SS
 */
export function formatDuration(seconds) {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = Math.floor(seconds % 60);
  
  if (hours > 0) {
    return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  }
  return `${minutes}:${secs.toString().padStart(2, '0')}`;
}

/**
 * Validate video file format
 */
export function validateVideoFormat(filePath) {
  const validFormats = ['.mp4', '.avi', '.mov', '.mkv', '.webm'];
  const ext = getFileExtension(filePath);
  
  if (!validFormats.includes(ext)) {
    throw new Error(`Unsupported video format: ${ext}. Supported: ${validFormats.join(', ')}`);
  }
  
  if (!existsSync(filePath)) {
    throw new Error(`Video file not found: ${filePath}`);
  }
  
  return true;
}

/**
 * Sleep/delay utility
 */
export function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * Retry function with exponential backoff
 */
export async function retry(fn, maxRetries = 3, delay = 1000) {
  for (let i = 0; i < maxRetries; i++) {
    try {
      return await fn();
    } catch (error) {
      if (i === maxRetries - 1) {
        throw error;
      }
      const waitTime = delay * Math.pow(2, i);
      console.log(`Retry ${i + 1}/${maxRetries} after ${waitTime}ms...`);
      await sleep(waitTime);
    }
  }
}
