"""
FastAPI Application for Dubbing Pipeline
Provides endpoints for transcription, translation, emotion detection, TTS, and lip-sync
"""

import os
import sys
import torch
import logging
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

# Import services
from services.transcribe import transcribe_router, load_whisper_model
from services.translate import translate_router, load_translation_model
from services.emotion import emotion_router, load_emotion_model
from services.tts import tts_router, load_tts_model
from services.lipsync import lipsync_router, load_lipsync_model

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
MODEL_DIR = os.getenv("MODEL_CACHE_DIR", "./models")
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# Global model storage
models = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load models on startup, cleanup on shutdown"""
    logger.info("Starting up...")
    logger.info(f"Device: {DEVICE}")
    logger.info(f"Model directory: {MODEL_DIR}")
    
    # Check CUDA availability
    if torch.cuda.is_available():
        logger.info(f"CUDA available: {torch.cuda.get_device_name(0)}")
        logger.info(f"CUDA version: {torch.version.cuda}")
    else:
        logger.warning("CUDA not available, using CPU (will be slower)")
    
    # Load models
    try:
        logger.info("Loading Whisper model...")
        models["whisper"] = load_whisper_model(MODEL_DIR, DEVICE)
        logger.info("✓ Whisper model loaded")
        
        logger.info("Loading translation model...")
        models["translate"] = load_translation_model(MODEL_DIR, DEVICE)
        logger.info("✓ Translation model loaded")
        
        logger.info("Loading emotion model...")
        models["emotion"] = load_emotion_model(MODEL_DIR, DEVICE)
        logger.info("✓ Emotion model loaded")
        
        logger.info("Loading TTS model...")
        models["tts"] = load_tts_model(MODEL_DIR, DEVICE)
        logger.info("✓ TTS model loaded")
        
        logger.info("Loading lip-sync model...")
        models["lipsync"] = load_lipsync_model(MODEL_DIR)
        logger.info("✓ Lip-sync model loaded")
        
        logger.info("All models loaded successfully!")
    except Exception as e:
        logger.error(f"Error loading models: {e}")
        logger.error("Some endpoints may not work correctly")
    
    yield
    
    # Cleanup on shutdown
    logger.info("Shutting down...")
    models.clear()


# Create FastAPI app
app = FastAPI(
    title="Dubbing Pipeline API",
    description="API for video dubbing pipeline with transcription, translation, TTS, and lip-sync",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(transcribe_router, prefix="/transcribe", tags=["transcription"])
app.include_router(translate_router, prefix="/translate", tags=["translation"])
app.include_router(emotion_router, prefix="/emotion", tags=["emotion"])
app.include_router(tts_router, prefix="/tts", tags=["tts"])
app.include_router(lipsync_router, prefix="/lipsync", tags=["lipsync"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Dubbing Pipeline API",
        "version": "1.0.0",
        "device": DEVICE,
        "cuda_available": torch.cuda.is_available()
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "device": DEVICE,
        "models_loaded": list(models.keys())
    }


@app.get("/stats")
async def get_stats():
    """Get system statistics and cost tracking"""
    import subprocess
    import time
    
    stats = {
        "device": DEVICE,
        "cuda_available": torch.cuda.is_available(),
        "models_loaded": list(models.keys())
    }
    
    # GPU stats if available
    if torch.cuda.is_available():
        try:
            gpu_info = subprocess.check_output(
                ["nvidia-smi", "--query-gpu=utilization.gpu,memory.used,memory.total", "--format=csv,noheader,nounits"],
                stderr=subprocess.DEVNULL
            ).decode().strip()
            stats["gpu_info"] = gpu_info
        except:
            stats["gpu_info"] = "Unable to get GPU info"
    
    # Uptime
    try:
        uptime = subprocess.check_output(["uptime", "-p"], stderr=subprocess.DEVNULL).decode().strip()
        stats["uptime"] = uptime
    except:
        stats["uptime"] = "Unable to get uptime"
    
    return stats


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("API_PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
