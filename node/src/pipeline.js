/**
 * Pipeline Orchestrator
 * Coordinates all steps of the dubbing pipeline
 */

import axios from 'axios';
import ffmpeg from 'fluent-ffmpeg';
import { promisify } from 'util';
import config, { getApiUrl, ensureDirectories } from './config.js';
import {
  getTempFilePath,
  getVideoDuration,
  getAudioDuration,
  formatDuration,
  validateVideoFormat,
  cleanupTempFiles,
  ensureDir
} from './utils.js';

// Ensure directories exist
ensureDirectories();

/**
 * Extract audio from video file
 */
export async function extractAudio(inputVideo, outputAudio) {
  console.log(`\n[1/8] Extracting audio from video...`);
  console.log(`  Input: ${inputVideo}`);
  console.log(`  Output: ${outputAudio}`);
  
  validateVideoFormat(inputVideo);
  ensureDir(config.tempDir);
  
  return new Promise((resolve, reject) => {
    ffmpeg(inputVideo)
      .audioCodec('pcm_s16le')
      .audioFrequency(16000)
      .audioChannels(1)
      .format('wav')
      .on('start', (cmd) => {
        console.log(`  FFmpeg command: ${cmd}`);
      })
      .on('progress', (progress) => {
        if (progress.percent) {
          process.stdout.write(`\r  Progress: ${Math.round(progress.percent)}%`);
        }
      })
      .on('end', async () => {
        console.log(`\n  ✓ Audio extracted successfully`);
        
        try {
          const duration = await getAudioDuration(outputAudio);
          console.log(`  Duration: ${formatDuration(duration)}`);
          resolve({
            success: true,
            path: outputAudio,
            duration: duration
          });
        } catch (err) {
          reject(new Error(`Failed to get audio duration: ${err.message}`));
        }
      })
      .on('error', (err) => {
        console.error(`  ✗ Error extracting audio: ${err.message}`);
        reject(new Error(`Audio extraction failed: ${err.message}`));
      })
      .save(outputAudio);
  });
}

/**
 * Transcribe audio segments
 */
export async function transcribeSegments(audioPath) {
  console.log(`\n[2/8] Transcribing audio...`);
  
  try {
    const FormData = (await import('form-data')).default;
    const fs = await import('fs');
    const formData = new FormData();
    formData.append('file', fs.createReadStream(audioPath), {
      filename: 'audio.wav',
      contentType: 'audio/wav'
    });
    
    console.log(`  Calling transcription API...`);
    const response = await axios.post(
      getApiUrl('/transcribe'),
      formData,
      {
        headers: formData.getHeaders(),
        timeout: 600000 // 10 minutes for long audio
      }
    );
    
    const segments = response.data.segments || [];
    console.log(`  ✓ Transcription completed: ${segments.length} segments`);
    console.log(`  Language detected: ${response.data.language}`);
    console.log(`  Processing time: ${response.data.processing_time}s`);
    
    return segments;
  } catch (error) {
    if (error.response) {
      throw new Error(`Transcription API error: ${error.response.data.detail || error.message}`);
    }
    throw new Error(`Transcription failed: ${error.message}`);
  }
}

/**
 * Detect emotions for each segment
 */
export async function detectEmotions(segments) {
  console.log(`\n[3/8] Detecting emotions...`);
  
  const emotions = [];
  
  for (let i = 0; i < segments.length; i++) {
    const segment = segments[i];
    process.stdout.write(`\r  Processing segment ${i + 1}/${segments.length}...`);
    
    try {
      const response = await axios.post(getApiUrl('/emotion'), {
        text: segment.text
      });
      
      emotions.push({
        segmentId: segment.id,
        emotion: response.data.emotion,
        confidence: response.data.confidence
      });
    } catch (error) {
      console.warn(`\n  ⚠ Failed to detect emotion for segment ${i}: ${error.message}`);
      emotions.push({
        segmentId: segment.id,
        emotion: 'neutral',
        confidence: 0
      });
    }
  }
  
  console.log(`\n  ✓ Emotion detection completed`);
  return emotions;
}

/**
 * Translate segments
 */
export async function translateSegments(segments, emotions) {
  console.log(`\n[4/8] Translating segments...`);
  console.log(`  Source: ${config.sourceLang} → Target: ${config.targetLang}`);
  
  const translatedSegments = [];
  
  for (let i = 0; i < segments.length; i++) {
    const segment = segments[i];
    const emotion = emotions.find(e => e.segmentId === segment.id)?.emotion || 'neutral';
    
    process.stdout.write(`\r  Translating segment ${i + 1}/${segments.length}...`);
    
    try {
      const response = await axios.post(getApiUrl('/translate'), {
        text: segment.text,
        source_lang: config.sourceLang,
        target_lang: config.targetLang,
        emotion: emotion
      });
      
      translatedSegments.push({
        ...segment,
        translated_text: response.data.translated_text,
        emotion: emotion
      });
    } catch (error) {
      if (error.response) {
        throw new Error(`Translation API error: ${error.response.data.detail || error.message}`);
      }
      throw new Error(`Translation failed: ${error.message}`);
    }
  }
  
  console.log(`\n  ✓ Translation completed`);
  return translatedSegments;
}

/**
 * Extract reference audio for voice cloning
 */
export async function extractReferenceAudio(audioPath, duration = 10) {
  console.log(`\n[5/8] Extracting reference audio (first ${duration}s)...`);
  
  const referenceAudioPath = getTempFilePath('reference_audio', '.wav');
  ensureDir(config.tempDir);
  
  return new Promise((resolve, reject) => {
    ffmpeg(audioPath)
      .setStartTime(0)
      .setDuration(duration)
      .audioCodec('pcm_s16le')
      .audioFrequency(16000)
      .audioChannels(1)
      .format('wav')
      .on('end', () => {
        console.log(`  ✓ Reference audio extracted: ${referenceAudioPath}`);
        resolve(referenceAudioPath);
      })
      .on('error', (err) => {
        reject(new Error(`Failed to extract reference audio: ${err.message}`));
      })
      .save(referenceAudioPath);
  });
}

/**
 * Generate dubbed audio for all segments
 */
export async function generateDubbedAudio(translatedSegments, referenceAudioPath, originalVideoPath) {
  console.log(`\n[6/8] Generating dubbed audio...`);
  
  const audioSegments = [];
  const total = translatedSegments.length;
  
  for (let i = 0; i < translatedSegments.length; i++) {
    const segment = translatedSegments[i];
    const outputPath = getTempFilePath(`segment_${segment.id}`, '.wav');
    
    process.stdout.write(`\r  Generating speech ${i + 1}/${total}...`);
    
    try {
      const response = await axios.post(getApiUrl('/tts'), {
        text: segment.translated_text,
        reference_audio: referenceAudioPath,
        language: 'uz', // Uzbek
        output_path: outputPath,
        emotion: segment.emotion
      });
      
      audioSegments.push({
        segmentId: segment.id,
        path: outputPath,
        start: segment.start,
        end: segment.end,
        duration: response.data.duration
      });
    } catch (error) {
      if (error.response) {
        throw new Error(`TTS API error: ${error.response.data.detail || error.message}`);
      }
      throw new Error(`TTS generation failed: ${error.message}`);
    }
  }
  
  console.log(`\n  ✓ Dubbed audio generated for ${audioSegments.length} segments`);
  return audioSegments;
}

/**
 * Combine audio segments into single file
 */
export async function combineAudioSegments(audioSegments, outputPath) {
  console.log(`\n[7/8] Combining audio segments...`);
  
  ensureDir(config.tempDir);
  
  // Create a temporary file list for ffmpeg concat
  const fileListPath = getTempFilePath('audio_list', '.txt');
  const fs = await import('fs');
  
  const fileList = audioSegments
    .sort((a, b) => a.start - b.start)
    .map(seg => `file '${seg.path.replace(/\\/g, '/')}'`)
    .join('\n');
  
  fs.writeFileSync(fileListPath, fileList);
  
  return new Promise((resolve, reject) => {
    ffmpeg()
      .input(fileListPath)
      .inputOptions(['-f', 'concat', '-safe', '0'])
      .audioCodec('pcm_s16le')
      .audioFrequency(16000)
      .audioChannels(1)
      .format('wav')
      .on('end', () => {
        console.log(`  ✓ Audio segments combined: ${outputPath}`);
        // Clean up file list
        try {
          fs.unlinkSync(fileListPath);
        } catch (err) {
          // Ignore
        }
        resolve(outputPath);
      })
      .on('error', (err) => {
        reject(new Error(`Failed to combine audio segments: ${err.message}`));
      })
      .save(outputPath);
  });
}

/**
 * Sync lips with audio (Wav2Lip)
 */
export async function syncLips(videoPath, audioPath, outputPath) {
  console.log(`\n[8/8] Syncing lips with audio...`);
  
  try {
    const response = await axios.post(getApiUrl('/lipsync'), {
      video_path: videoPath,
      audio_path: audioPath,
      output_path: outputPath
    });
    
    console.log(`  ✓ Lip-sync completed: ${outputPath}`);
    return response.data;
  } catch (error) {
    if (error.response) {
      throw new Error(`Lip-sync API error: ${error.response.data.detail || error.message}`);
    }
    throw new Error(`Lip-sync failed: ${error.message}`);
  }
}

/**
 * Assemble final video
 */
export async function assembleFinalVideo(videoPath, audioPath, outputPath) {
  console.log(`\n[9/9] Assembling final video...`);
  console.log(`  Video: ${videoPath}`);
  console.log(`  Audio: ${audioPath}`);
  console.log(`  Output: ${outputPath}`);
  
  ensureDir(config.outputDir);
  
  return new Promise((resolve, reject) => {
    ffmpeg(videoPath)
      .input(audioPath)
      .videoCodec('copy')
      .audioCodec('aac')
      .audioBitrate('192k')
      .on('start', (cmd) => {
        console.log(`  FFmpeg command: ${cmd}`);
      })
      .on('progress', (progress) => {
        if (progress.percent) {
          process.stdout.write(`\r  Progress: ${Math.round(progress.percent)}%`);
        }
      })
      .on('end', () => {
        console.log(`\n  ✓ Final video assembled: ${outputPath}`);
        resolve(outputPath);
      })
      .on('error', (err) => {
        reject(new Error(`Failed to assemble final video: ${err.message}`));
      })
      .save(outputPath);
  });
}

/**
 * Clean up temporary files
 */
export async function cleanup() {
  console.log(`\nCleaning up temporary files...`);
  cleanupTempFiles(config.tempDir);
}

/**
 * Main pipeline function
 */
export async function runPipeline(inputVideo, outputVideo) {
  const startTime = Date.now();
  
  try {
    console.log('='.repeat(60));
    console.log('Dubbing Pipeline Started');
    console.log('='.repeat(60));
    console.log(`Input: ${inputVideo}`);
    console.log(`Output: ${outputVideo}`);
    console.log(`Source: ${config.sourceLang} → Target: ${config.targetLang}`);
    
    // Step 1: Extract audio
    const audioPath = getTempFilePath('original_audio', '.wav');
    const audioInfo = await extractAudio(inputVideo, audioPath);
    
    // Step 2: Transcribe
    const segments = await transcribeSegments(audioPath);
    
    // Step 3: Detect emotions
    const emotions = await detectEmotions(segments);
    
    // Step 4: Translate
    const translatedSegments = await translateSegments(segments, emotions);
    
    // Step 5: Extract reference audio
    const referenceAudioPath = await extractReferenceAudio(audioPath, config.referenceAudioDuration);
    
    // Step 6: Generate dubbed audio
    const audioSegments = await generateDubbedAudio(translatedSegments, referenceAudioPath, inputVideo);
    
    // Step 7: Combine audio segments
    const dubbedAudioPath = getTempFilePath('dubbed_audio', '.wav');
    await combineAudioSegments(audioSegments, dubbedAudioPath);
    
    // Step 8: Sync lips
    const syncedVideoPath = getTempFilePath('synced_video', '.mp4');
    await syncLips(inputVideo, dubbedAudioPath, syncedVideoPath);
    
    // Step 9: Assemble final video
    await assembleFinalVideo(syncedVideoPath, dubbedAudioPath, outputVideo);
    
    // Cleanup
    await cleanup();
    
    const totalTime = (Date.now() - startTime) / 1000;
    console.log('\n' + '='.repeat(60));
    console.log('Pipeline Completed Successfully!');
    console.log('='.repeat(60));
    console.log(`Total time: ${formatDuration(totalTime)}`);
    console.log(`Output: ${outputVideo}`);
    
    return {
      success: true,
      outputPath: outputVideo,
      processingTime: totalTime
    };
    
  } catch (error) {
    console.error('\n' + '='.repeat(60));
    console.error('Pipeline Failed');
    console.error('='.repeat(60));
    console.error(`Error: ${error.message}`);
    
    // Cleanup on error
    await cleanup();
    
    throw error;
  }
}
