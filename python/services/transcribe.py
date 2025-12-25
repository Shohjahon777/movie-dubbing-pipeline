"""
Whisper Transcription Service
Provides audio transcription with word-level timestamps
"""

import os
import time
import logging
import whisper
# import torch
from fastapi import APIRouter, UploadFile, File, HTTPException
from pathlib import Path
import tempfile

logger = logging.getLogger(__name__)

transcribe_router = APIRouter()
whisper_model = None


def load_whisper_model(model_dir: str, device: str):
    """Load Whisper model"""
    global whisper_model
    try:
        model_name = "large-v3"
        logger.info(f"Loading Whisper model: {model_name}")
        whisper_model = whisper.load_model(
            model_name,
            device=device,
            download_root=os.path.join(model_dir, "whisper")
        )
        logger.info("Whisper model loaded successfully")
        return whisper_model
    except Exception as e:
        logger.error(f"Error loading Whisper model: {e}")
        raise


@transcribe_router.post("")
async def transcribe_audio(file: UploadFile = File(...)):
    """
    Transcribe audio file to text with word-level timestamps
    
    Args:
        file: Audio file (WAV, MP3, etc.)
    
    Returns:
        JSON with segments containing text, start, end timestamps
    """
    if whisper_model is None:
        raise HTTPException(status_code=503, detail="Whisper model not loaded")
    
    # Validate file type
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
    
    # Save uploaded file temporarily
    temp_path = None
    try:
        # Create temp file
        suffix = Path(file.filename).suffix or ".wav"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
            temp_path = tmp_file.name
            content = await file.read()
            tmp_file.write(content)
        
        logger.info(f"Transcribing audio file: {file.filename}")
        start_time = time.time()
        
        # Transcribe with word-level timestamps
        result = whisper_model.transcribe(
            temp_path,
            language="en",  # Can be auto-detected by setting to None
            word_timestamps=True,
            task="transcribe"
        )
        
        processing_time = time.time() - start_time
        logger.info(f"Transcription completed in {processing_time:.2f} seconds")
        
        # Format segments
        segments = []
        for i, seg in enumerate(result["segments"]):
            segments.append({
                "id": i,
                "start": round(seg["start"], 2),
                "end": round(seg["end"], 2),
                "text": seg["text"].strip(),
                "words": [
                    {
                        "word": word["word"],
                        "start": round(word["start"], 2),
                        "end": round(word["end"], 2)
                    }
                    for word in seg.get("words", [])
                ] if "words" in seg else []
            })
        
        return {
            "segments": segments,
            "language": result.get("language", "en"),
            "processing_time": round(processing_time, 2)
        }
    
    except Exception as e:
        logger.error(f"Error transcribing audio: {e}")
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")
    
    finally:
        # Cleanup temp file
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass
