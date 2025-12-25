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


def load_translation_model(model_dir: str, device: str, force_reload: bool = False):
    """Load NLLB translation model with memory optimizations (lazy loading)"""
    global translation_model, translation_tokenizer
    
    # Skip if already loaded (unless force_reload)
    if translation_model is not None and translation_tokenizer is not None and not force_reload:
        logger.info("Translation model already loaded")
        return translation_model
    
    try:
        # Use smaller model to fit in memory (600M instead of 3.3B)
        # Still supports 200 languages including Uzbek
        model_name = "facebook/nllb-200-distilled-600M"
        logger.info(f"Loading translation model: {model_name} (optimized for memory)")
        
        cache_dir = os.path.join(model_dir, "transformers")
        os.makedirs(cache_dir, exist_ok=True)
        
        translation_tokenizer = AutoTokenizer.from_pretrained(
            model_name,
            cache_dir=cache_dir
        )
        
        # Memory-optimized loading
        load_kwargs = {
            "cache_dir": cache_dir,
            "low_cpu_mem_usage": True,  # Reduces peak memory during loading
        }
        
        # For CUDA, use device_map for automatic device placement
        if device == "cuda":
            load_kwargs["device_map"] = "auto"
        
        translation_model = AutoModelForSeq2SeqLM.from_pretrained(
            model_name,
            **load_kwargs
        )
        
        # Move to device if not using device_map
        if device != "cuda" or "device_map" not in load_kwargs:
            translation_model = translation_model.to(device)
        
        # Set to evaluation mode to save memory
        translation_model.eval()
        
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
    # Lazy load model on first request to save startup memory
    if translation_model is None or translation_tokenizer is None:
        logger.info("Translation model not loaded, loading now...")
        # Get config from environment (same as app.py)
        model_dir = os.getenv("MODEL_CACHE_DIR", "./models")
        device = "cuda" if torch.cuda.is_available() else "cpu"
        load_translation_model(model_dir, device)
        # Clean up memory after loading
        import gc
        gc.collect()
        if device == "cuda":
            torch.cuda.empty_cache()
    
    if translation_model is None or translation_tokenizer is None:
        raise HTTPException(status_code=503, detail="Translation model not loaded")
    
    try:
        # Validate language codes
        source_lang = request.source_lang
        target_lang = request.target_lang
        
        # Get target language token ID
        # Check if lang_code_to_id attribute exists
        if not hasattr(translation_tokenizer, 'lang_code_to_id'):
            logger.error("Tokenizer missing lang_code_to_id attribute")
            raise HTTPException(
                status_code=500,
                detail="Tokenizer missing lang_code_to_id attribute. Model may not be fully loaded."
            )
        
        # Get available language codes for debugging
        available_langs = list(translation_tokenizer.lang_code_to_id.keys())
        logger.debug(f"Total available language codes: {len(available_langs)}")
        
        # Try to get target language token ID, with fallbacks
        target_token_id = None
        original_target_lang = target_lang
        
        # Define alternative code mappings for Uzbek
        uzbek_alternatives = {
            'uzb_Latn': ['uzb_Latn', 'uzb', 'uz_Latn', 'uz', 'uzb_Latin'],
            'uzb_Cyrl': ['uzb_Cyrl', 'uz_Cyrl', 'uzb_Cyrillic']
        }
        
        # Try the requested code first
        if target_lang in translation_tokenizer.lang_code_to_id:
            target_token_id = translation_tokenizer.lang_code_to_id[target_lang]
        else:
            # Try alternatives
            alternatives = uzbek_alternatives.get(target_lang, [target_lang])
            for alt_code in alternatives:
                if alt_code in translation_tokenizer.lang_code_to_id:
                    target_token_id = translation_tokenizer.lang_code_to_id[alt_code]
                    logger.info(f"Using alternative language code: {alt_code} (instead of {target_lang})")
                    target_lang = alt_code  # Update to the code that worked
                    break
        
        # If still not found, provide helpful error message
        if target_token_id is None:
            # Find all Uzbek-related codes
            uzb_codes = [code for code in available_langs if 'uzb' in code.lower() or code.lower().startswith('uz')]
            uzb_codes = uzb_codes[:10]  # Limit to first 10
            
            error_msg = f"Unsupported target language: {original_target_lang}.\n"
            if uzb_codes:
                error_msg += f"Found Uzbek-related codes: {', '.join(uzb_codes)}.\n"
            error_msg += f"Total available codes: {len(available_langs)}. Please check NLLB documentation for correct code format."
            
            logger.error(f"Language code not found. Requested: {original_target_lang}, Available Uzbek codes: {uzb_codes}")
            raise HTTPException(status_code=400, detail=error_msg)
        
        logger.info(f"Translating from {source_lang} to {target_lang}")
        
        # Validate source language code
        if source_lang not in translation_tokenizer.lang_code_to_id:
            # Try common alternatives for English
            eng_alternatives = ['eng_Latn', 'eng', 'en', 'en_Latn']
            for alt_code in eng_alternatives:
                if alt_code in translation_tokenizer.lang_code_to_id:
                    source_lang = alt_code
                    logger.info(f"Using alternative source code: {alt_code}")
                    break
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported source language: {request.source_lang}. Available English codes: {[c for c in available_langs if 'eng' in c.lower() or c.lower().startswith('en')][:5]}"
                )
        
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


@translate_router.get("/languages")
async def list_supported_languages():
    """
    List all supported language codes in the translation model
    Useful for debugging and finding correct language codes
    """
    # Lazy load model if needed
    if translation_tokenizer is None:
        model_dir = os.getenv("MODEL_CACHE_DIR", "./models")
        device = "cuda" if torch.cuda.is_available() else "cpu"
        try:
            load_translation_model(model_dir, device)
        except Exception as e:
            raise HTTPException(
                status_code=503,
                detail=f"Could not load translation model: {str(e)}"
            )
    
    if not hasattr(translation_tokenizer, 'lang_code_to_id'):
        raise HTTPException(
            status_code=500,
            detail="Tokenizer missing lang_code_to_id attribute"
        )
    
    available_langs = list(translation_tokenizer.lang_code_to_id.keys())
    
    # Find Uzbek-related codes
    uzb_codes = [code for code in available_langs if 'uzb' in code.lower() or code.lower().startswith('uz')]
    
    # Find English-related codes
    eng_codes = [code for code in available_langs if 'eng' in code.lower() or code.lower().startswith('en')]
    
    return {
        "total_languages": len(available_langs),
        "uzbek_codes": uzb_codes,
        "english_codes": eng_codes[:10],
        "all_codes": sorted(available_langs)  # Return all for reference
    }
