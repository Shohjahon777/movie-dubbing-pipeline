#!/usr/bin/env python3
"""
Model Downloader Script
Downloads and caches all required ML models for the dubbing pipeline.
Estimated total size: ~15-20GB
"""

import os
import sys
import argparse
import shutil
from pathlib import Path
from tqdm import tqdm
import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM, AutoModel, AutoProcessor
import whisper
from TTS.api import TTS
import requests

# Model configurations
MODELS = {
    "whisper": {
        "name": "large-v3",
        "type": "whisper",
        "size_gb": 3.0,
        "description": "Whisper large-v3 for transcription"
    },
    "nllb": {
        "name": "facebook/nllb-200-3.3B",
        "type": "transformers",
        "size_gb": 6.6,
        "description": "NLLB-200-3.3B for translation"
    },
    "emotion": {
        "name": "j-hartmann/emotion-english-distilroberta-base",
        "type": "transformers",
        "size_gb": 0.25,
        "description": "Emotion detection model"
    },
    "xtts": {
        "name": "tts_models/multilingual/multi-dataset/xtts_v2",
        "type": "tts",
        "size_gb": 1.8,
        "description": "Coqui XTTS-v2 for voice cloning"
    },
    "wav2lip": {
        "name": "wav2lip_gan",
        "type": "checkpoint",
        "url": "https://github.com/Rudrabha/Wav2Lip/releases/download/v1.0.0/wav2lip_gan.pth",
        "size_gb": 0.4,
        "description": "Wav2Lip checkpoint for lip sync"
    }
}


def get_disk_space(path):
    """Get available disk space in GB"""
    stat = shutil.disk_usage(path)
    return stat.free / (1024 ** 3)


def check_model_exists(model_dir, model_key):
    """Check if model is already downloaded"""
    model_config = MODELS[model_key]
    
    if model_key == "wav2lip":
        checkpoint_path = os.path.join(model_dir, "wav2lip_gan.pth")
        return os.path.exists(checkpoint_path) and os.path.getsize(checkpoint_path) > 1000000
    
    if model_key == "whisper":
        # Check if whisper model cache exists
        whisper_cache = os.path.join(model_dir, "whisper", model_config["name"])
        return os.path.exists(whisper_cache)
    
    if model_key == "xtts":
        # XTTS models are cached by TTS library
        return True  # Will be checked during actual download
    
    # For transformers models, check cache directory
    cache_dir = os.path.join(model_dir, "transformers")
    model_name = model_config["name"].replace("/", "--")
    model_path = os.path.join(cache_dir, model_name)
    return os.path.exists(model_path)


def download_wav2lip(model_dir, url):
    """Download Wav2Lip checkpoint"""
    checkpoint_path = os.path.join(model_dir, "wav2lip_gan.pth")
    
    if os.path.exists(checkpoint_path):
        print(f"  ✓ Wav2Lip checkpoint already exists")
        return True
    
    print(f"  Downloading Wav2Lip checkpoint...")
    try:
        response = requests.get(url, stream=True)
        total_size = int(response.headers.get('content-length', 0))
        
        with open(checkpoint_path, 'wb') as f, tqdm(
            desc="  Progress",
            total=total_size,
            unit='B',
            unit_scale=True,
            unit_divisor=1024,
        ) as bar:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    bar.update(len(chunk))
        
        print(f"  ✓ Wav2Lip checkpoint downloaded")
        return True
    except Exception as e:
        print(f"  ✗ Error downloading Wav2Lip: {e}")
        return False


def download_whisper(model_dir, model_name):
    """Download Whisper model"""
    print(f"  Loading Whisper model (this will download if not cached)...")
    try:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        model = whisper.load_model(model_name, device=device, download_root=os.path.join(model_dir, "whisper"))
        print(f"  ✓ Whisper model loaded")
        return True
    except Exception as e:
        print(f"  ✗ Error loading Whisper model: {e}")
        return False


def download_transformers_model(model_dir, model_name):
    """Download transformers model"""
    print(f"  Loading transformers model (this will download if not cached)...")
    try:
        cache_dir = os.path.join(model_dir, "transformers")
        os.makedirs(cache_dir, exist_ok=True)
        
        # Try loading tokenizer first (smaller, faster check)
        tokenizer = AutoTokenizer.from_pretrained(
            model_name,
            cache_dir=cache_dir,
            resume_download=True
        )
        
        # Load model with progress
        model = AutoModelForSeq2SeqLM.from_pretrained(
            model_name,
            cache_dir=cache_dir,
            resume_download=True
        )
        
        print(f"  ✓ Transformers model loaded")
        return True
    except Exception as e:
        print(f"  ✗ Error loading transformers model: {e}")
        return False


def download_emotion_model(model_dir, model_name):
    """Download emotion detection model"""
    print(f"  Loading emotion model (this will download if not cached)...")
    try:
        cache_dir = os.path.join(model_dir, "transformers")
        os.makedirs(cache_dir, exist_ok=True)
        
        tokenizer = AutoTokenizer.from_pretrained(
            model_name,
            cache_dir=cache_dir,
            resume_download=True
        )
        
        model = AutoModel.from_pretrained(
            model_name,
            cache_dir=cache_dir,
            resume_download=True
        )
        
        print(f"  ✓ Emotion model loaded")
        return True
    except Exception as e:
        print(f"  ✗ Error loading emotion model: {e}")
        return False


def download_xtts(model_dir):
    """Download XTTS model"""
    print(f"  Loading XTTS model (this will download if not cached)...")
    try:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2", gpu=(device == "cuda"))
        print(f"  ✓ XTTS model loaded")
        return True
    except Exception as e:
        print(f"  ✗ Error loading XTTS model: {e}")
        return False


def download_model(model_key, model_dir, force=False):
    """Download a single model"""
    model_config = MODELS[model_key]
    
    print(f"\n[{model_key.upper()}] {model_config['description']}")
    print(f"  Estimated size: {model_config['size_gb']:.2f} GB")
    
    # Check if already downloaded
    if not force and check_model_exists(model_dir, model_key):
        print(f"  ✓ Model already exists, skipping...")
        return True
    
    # Download based on model type
    success = False
    if model_key == "wav2lip":
        success = download_wav2lip(model_dir, model_config["url"])
    elif model_key == "whisper":
        success = download_whisper(model_dir, model_config["name"])
    elif model_key == "nllb":
        success = download_transformers_model(model_dir, model_config["name"])
    elif model_key == "emotion":
        success = download_emotion_model(model_dir, model_config["name"])
    elif model_key == "xtts":
        success = download_xtts(model_dir)
    
    return success


def main():
    parser = argparse.ArgumentParser(description="Download models for dubbing pipeline")
    parser.add_argument(
        "--model-dir",
        type=str,
        default="./models",
        help="Directory to store models (default: ./models)"
    )
    parser.add_argument(
        "--model",
        type=str,
        choices=list(MODELS.keys()) + ["all"],
        default="all",
        help="Model to download (default: all)"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-download even if model exists"
    )
    
    args = parser.parse_args()
    
    model_dir = Path(args.model_dir).resolve()
    model_dir.mkdir(parents=True, exist_ok=True)
    
    # Check disk space
    available_space = get_disk_space(model_dir)
    total_size = sum(m["size_gb"] for m in MODELS.values())
    
    print("=" * 60)
    print("Model Downloader for Dubbing Pipeline")
    print("=" * 60)
    print(f"Model directory: {model_dir}")
    print(f"Available disk space: {available_space:.2f} GB")
    print(f"Estimated total size: {total_size:.2f} GB")
    print("=" * 60)
    
    if available_space < total_size:
        print(f"\n⚠ WARNING: Available disk space ({available_space:.2f} GB) is less than")
        print(f"  estimated total size ({total_size:.2f} GB).")
        response = input("  Continue anyway? (y/N): ")
        if response.lower() != 'y':
            print("Aborted.")
            sys.exit(1)
    
    # Determine which models to download
    if args.model == "all":
        models_to_download = list(MODELS.keys())
    else:
        models_to_download = [args.model]
    
    # Download models
    results = {}
    for model_key in models_to_download:
        results[model_key] = download_model(model_key, str(model_dir), args.force)
    
    # Summary
    print("\n" + "=" * 60)
    print("Download Summary")
    print("=" * 60)
    
    for model_key, success in results.items():
        status = "✓ SUCCESS" if success else "✗ FAILED"
        print(f"{model_key.upper():15} {status}")
    
    failed = [k for k, v in results.items() if not v]
    if failed:
        print(f"\n⚠ Failed to download: {', '.join(failed)}")
        sys.exit(1)
    else:
        print("\n✓ All models downloaded successfully!")
        
        # Show disk usage
        model_size = sum(
            os.path.getsize(os.path.join(model_dir, f))
            for f in os.listdir(model_dir)
            if os.path.isfile(os.path.join(model_dir, f))
        )
        for root, dirs, files in os.walk(model_dir):
            for file in files:
                filepath = os.path.join(root, file)
                try:
                    model_size += os.path.getsize(filepath)
                except:
                    pass
        
        print(f"Total disk usage: {model_size / (1024**3):.2f} GB")


if __name__ == "__main__":
    main()
