"""
Emotion Detection Service
Detects emotions in text using DistilRoBERTa model
"""

import os
import logging
import torch
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch.nn.functional as F

logger = logging.getLogger(__name__)

emotion_router = APIRouter()
emotion_model = None
emotion_tokenizer = None

# Emotion labels (matching the model)
EMOTION_LABELS = ["neutral", "joy", "sadness", "anger", "fear", "surprise"]


class EmotionRequest(BaseModel):
    text: str


def load_emotion_model(model_dir: str, device: str):
    """Load emotion detection model"""
    global emotion_model, emotion_tokenizer
    
    try:
        model_name = "j-hartmann/emotion-english-distilroberta-base"
        logger.info(f"Loading emotion model: {model_name}")
        
        cache_dir = os.path.join(model_dir, "transformers")
        os.makedirs(cache_dir, exist_ok=True)
        
        emotion_tokenizer = AutoTokenizer.from_pretrained(
            model_name,
            cache_dir=cache_dir
        )
        
        emotion_model = AutoModelForSequenceClassification.from_pretrained(
            model_name,
            cache_dir=cache_dir
        ).to(device)
        
        emotion_model.eval()  # Set to evaluation mode
        
        logger.info("Emotion model loaded successfully")
        return emotion_model
    
    except Exception as e:
        logger.error(f"Error loading emotion model: {e}")
        raise


@emotion_router.post("")
async def detect_emotion(request: EmotionRequest):
    """
    Detect emotion in text
    
    Args:
        request: EmotionRequest with text
    
    Returns:
        JSON with detected emotion and confidence scores
    """
    if emotion_model is None or emotion_tokenizer is None:
        raise HTTPException(status_code=503, detail="Emotion model not loaded")
    
    try:
        logger.info(f"Detecting emotion in text: {request.text[:50]}...")
        
        # Tokenize input
        inputs = emotion_tokenizer(
            request.text,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=512
        )
        
        # Move to device
        device = next(emotion_model.parameters()).device
        inputs = {k: v.to(device) for k, v in inputs.items()}
        
        # Get predictions
        with torch.no_grad():
            outputs = emotion_model(**inputs)
            logits = outputs.logits
            probabilities = F.softmax(logits, dim=-1)
        
        # Get top emotion
        top_prob, top_idx = torch.max(probabilities, dim=-1)
        top_emotion = EMOTION_LABELS[top_idx.item()]
        top_confidence = top_prob.item()
        
        # Get all emotion scores
        emotion_scores = {}
        for i, label in enumerate(EMOTION_LABELS):
            emotion_scores[label] = round(probabilities[0][i].item(), 4)
        
        logger.info(f"Detected emotion: {top_emotion} (confidence: {top_confidence:.2f})")
        
        return {
            "emotion": top_emotion,
            "confidence": round(top_confidence, 4),
            "scores": emotion_scores,
            "text": request.text
        }
    
    except Exception as e:
        logger.error(f"Error detecting emotion: {e}")
        raise HTTPException(status_code=500, detail=f"Emotion detection failed: {str(e)}")
