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
    """Load Coqui XTTS model with terms acceptance"""
    global tts_model
    
    try:
        model_name = "tts_models/multilingual/multi-dataset/xtts_v2"
        logger.info(f"Loading TTS model: {model_name}")
        
        # Accept terms of service before loading (required for XTTS v2)
        try:
            from huggingface_hub import login
            # Try to accept terms - this may require HuggingFace token
            # If not logged in, user needs to accept manually first
            logger.info("Attempting to accept Coqui TTS terms of service...")
        except Exception as e:
            logger.warning(f"Could not automatically accept terms: {e}")
            logger.warning("You may need to accept terms manually at: https://huggingface.co/coqui/XTTS-v2")
        
        use_gpu = (device == "cuda")
        tts_model = TTS(model_name, gpu=use_gpu)
        
        logger.info("TTS model loaded successfully")
        return tts_model
    
    except Exception as e:
        error_msg = str(e)
        if "terms of service" in error_msg.lower():
            logger.error("TTS model requires accepting terms of service.")
            logger.error("Please run this command once to accept:")
            logger.error("  python -c \"from huggingface_hub import login; login()\"")
            logger.error("  Then visit: https://huggingface.co/coqui/XTTS-v2 and accept the terms")
            logger.error("Or set HUGGING_FACE_HUB_TOKEN environment variable")
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
    # Lazy load TTS model on first request (in case it failed at startup)
    if tts_model is None:
        logger.info("TTS model not loaded, attempting to load now...")
        model_dir = os.getenv("MODEL_CACHE_DIR", "./models")
        device = "cuda" if torch.cuda.is_available() else "cpu"
        try:
            load_tts_model(model_dir, device)
        except Exception as e:
            raise HTTPException(
                status_code=503, 
                detail=f"TTS model not loaded. Error: {str(e)}. You may need to accept terms at https://huggingface.co/coqui/XTTS-v2"
            )
    
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
