"""
Coqui XTTS Text-to-Speech Service
Generates voice-cloned speech from text
"""

import os
import logging
import torch
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from TTS.api import TTS
import soundfile as sf

logger = logging.getLogger(__name__)

tts_router = APIRouter()
tts_model = None


class TTSRequest(BaseModel):
    text: str
    reference_audio: str  # Path to reference audio file
    language: str = "uz"  # Language code (uz for Uzbek)
    output_path: str  # Path to save generated audio
    emotion: str = "neutral"  # Currently unused by XTTS


def load_tts_model(model_dir: str, device: str):
    """Load Coqui XTTS model"""
    global tts_model
    
    try:
        model_name = "tts_models/multilingual/multi-dataset/xtts_v2"
        logger.info(f"Loading TTS model: {model_name}")
        
        use_gpu = (device == "cuda")
        tts_model = TTS(model_name, gpu=use_gpu)
        
        logger.info("TTS model loaded successfully")
        return tts_model
    
    except Exception as e:
        logger.error(f"Error loading TTS model: {e}")
        raise


@tts_router.post("")
async def generate_speech(request: TTSRequest):
    """
    Generate speech from text using voice cloning
    
    Args:
        request: TTSRequest with text, reference_audio, language, output_path, emotion
    
    Returns:
        JSON with success status and audio duration
    """
    if tts_model is None:
        raise HTTPException(status_code=503, detail="TTS model not loaded")
    
    try:
        # Validate reference audio exists
        if not os.path.exists(request.reference_audio):
            raise HTTPException(
                status_code=400,
                detail=f"Reference audio file not found: {request.reference_audio}"
            )
        
        # Create output directory if needed
        output_dir = os.path.dirname(request.output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
        
        logger.info(f"Generating speech: {len(request.text)} chars, language: {request.language}")
        
        # Generate speech
        tts_model.tts_to_file(
            text=request.text,
            speaker_wav=request.reference_audio,
            language=request.language,
            file_path=request.output_path
        )
        
        # Get audio duration
        if os.path.exists(request.output_path):
            audio, sr = sf.read(request.output_path)
            duration = len(audio) / sr
        else:
            raise HTTPException(status_code=500, detail="Failed to generate audio file")
        
        logger.info(f"Speech generated: {request.output_path} ({duration:.2f}s)")
        
        return {
            "success": True,
            "output_path": request.output_path,
            "duration": round(duration, 2),
            "text": request.text,
            "language": request.language
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating speech: {e}")
        raise HTTPException(status_code=500, detail=f"TTS generation failed: {str(e)}")
