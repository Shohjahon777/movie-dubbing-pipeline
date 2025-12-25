"""
NLLB Translation Service
Provides translation from English to Uzbek using Facebook NLLB-200 model
"""

import os
import logging
import torch
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

logger = logging.getLogger(__name__)

translate_router = APIRouter()
translation_model = None
translation_tokenizer = None


class TranslationRequest(BaseModel):
    text: str
    source_lang: str = "eng_Latn"
    target_lang: str = "uzb_Latn"  # or "uzb_Cyrl" for Cyrillic script
    emotion: str = "neutral"  # Currently unused, reserved for future use


def load_translation_model(model_dir: str, device: str):
    """Load NLLB translation model"""
    global translation_model, translation_tokenizer
    
    try:
        model_name = "facebook/nllb-200-3.3B"
        logger.info(f"Loading translation model: {model_name}")
        
        cache_dir = os.path.join(model_dir, "transformers")
        os.makedirs(cache_dir, exist_ok=True)
        
        translation_tokenizer = AutoTokenizer.from_pretrained(
            model_name,
            cache_dir=cache_dir
        )
        
        translation_model = AutoModelForSeq2SeqLM.from_pretrained(
            model_name,
            cache_dir=cache_dir
        ).to(device)
        
        logger.info("Translation model loaded successfully")
        return translation_model
    
    except Exception as e:
        logger.error(f"Error loading translation model: {e}")
        raise


@translate_router.post("")
async def translate_text(request: TranslationRequest):
    """
    Translate text from source language to target language
    
    Args:
        request: TranslationRequest with text, source_lang, target_lang, emotion
    
    Returns:
        JSON with translated text
    """
    if translation_model is None or translation_tokenizer is None:
        raise HTTPException(status_code=503, detail="Translation model not loaded")
    
    try:
        # Validate language codes
        source_lang = request.source_lang
        target_lang = request.target_lang
        
        # Get target language token ID
        try:
            target_token_id = translation_tokenizer.lang_code_to_id[target_lang]
        except KeyError:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported target language: {target_lang}. Supported codes: uzb_Latn (default), uzb_Cyrl"
            )
        
        logger.info(f"Translating from {source_lang} to {target_lang}")
        
        # Tokenize input
        inputs = translation_tokenizer(
            request.text,
            return_tensors="pt",
            padding=True,
            src_lang=source_lang
        )
        
        # Move to device
        device = next(translation_model.parameters()).device
        inputs = {k: v.to(device) for k, v in inputs.items()}
        
        # Generate translation
        translated_tokens = translation_model.generate(
            **inputs,
            forced_bos_token_id=target_token_id,
            max_length=200,
            num_beams=5,
            early_stopping=True
        )
        
        # Decode translation
        translated_text = translation_tokenizer.batch_decode(
            translated_tokens,
            skip_special_tokens=True
        )[0]
        
        logger.info(f"Translation completed: {len(request.text)} -> {len(translated_text)} chars")
        
        return {
            "translated_text": translated_text,
            "source_lang": source_lang,
            "target_lang": target_lang,
            "original_text": request.text
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error translating text: {e}")
        raise HTTPException(status_code=500, detail=f"Translation failed: {str(e)}")
