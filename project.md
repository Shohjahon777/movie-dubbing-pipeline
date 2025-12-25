# Updated Cursor Prompt Series (Cloud GPU + Local Models)

Perfect! Let's redesign for **DigitalOcean GPU Droplet** with **local models only** (no API costs).

---

## **Your Setup Strategy**

### **Cloud Infrastructure** (DigitalOcean)
- Spin up a **GPU Droplet** (H100, A100, or RTX-enabled)
- Install: Ubuntu 22.04, CUDA 12.x, Docker
- Cost: ~$1-3/hour (turn off when not testing)
- Access: SSH + Jupyter for monitoring

### **Development Flow**
1. Code locally in **Cursor** (your laptop)
2. Push to GitHub (private repo)
3. Pull on DigitalOcean droplet
4. Run pipeline on cloud GPU
5. Download final video

### **Model Strategy** (All Local)
- **Whisper**: `large-v3` (local inference)
- **Translation**: `facebook/nllb-200-3.3B` or `google/madlad400-3b-mt` (no GPT-4)
- **Emotion**: `j-hartmann/emotion-english-distilroberta-base`
- **TTS**: Coqui XTTS v2 (local)
- **Lip-sync**: Wav2Lip (local)

### **Timeline**: 1 week bare-bones → 2 weeks polished

---

# **Revised Cursor Prompt Series**

---

## **PROMPT 1: Cloud-First Project Setup**

```
Create a Node.js + Python dubbing pipeline optimized for cloud GPU execution.

PROJECT STRUCTURE:
dubbing-mvp/
├── node/
│   ├── package.json
│   ├── src/
│   │   ├── index.js          # CLI entry point
│   │   ├── pipeline.js       # Step orchestrator
│   │   ├── config.js         # Environment-based config
│   │   └── utils.js          # File helpers
├── python/
│   ├── requirements.txt
│   ├── services/
│   │   ├── transcribe.py     # Whisper (local)
│   │   ├── translate.py      # NLLB translation (local)
│   │   ├── emotion.py        # Emotion detection (local)
│   │   ├── tts.py            # Coqui XTTS (local)
│   │   └── lipsync.py        # Wav2Lip (local)
│   ├── app.py                # FastAPI server
│   └── download_models.py    # Model downloader script
├── data/
│   ├── input/                # Upload videos here
│   ├── output/               # Final results
│   └── temp/                 # Intermediate files (auto-cleanup)
├── models/                   # Model cache (excluded from git)
├── docker/
│   ├── Dockerfile            # GPU-enabled container
│   └── docker-compose.yml
├── scripts/
│   ├── setup_droplet.sh      # DigitalOcean setup automation
│   └── deploy.sh             # Git pull + restart services
├── .env.example
├── .gitignore
└── README.md

REQUIREMENTS:
- Zero API dependencies (all models local)
- Optimized for GPU (CUDA detection)
- CPU fallback for development
- Minimal disk usage (models downloaded once)
- SSH-friendly (no GUI needed)

Generate:
1. package.json: axios, dotenv, fluent-ffmpeg, commander (for CLI args)
2. requirements.txt: fastapi, uvicorn, torch, transformers, TTS, openai-whisper, sentencepiece
3. .gitignore: models/, data/, *.pyc, node_modules/, .env
4. .env.example: CUDA_VISIBLE_DEVICES=0, MODEL_CACHE_DIR=./models
5. Basic folder structure with README placeholders

Keep it simple: This is a 1-week MVP, not production code.
```

---

## **PROMPT 2: DigitalOcean Setup Script**

```
Create an automated setup script for DigitalOcean GPU Droplet.

FILE: scripts/setup_droplet.sh

Script should:
1. Update system packages (apt update && upgrade)
2. Install CUDA 12.1 (check if already installed)
3. Install Python 3.10 + pip
4. Install Node.js 20.x (via NodeSource)
5. Install FFmpeg with GPU acceleration support
6. Install Docker + Docker Compose
7. Create project directory structure
8. Clone git repo (placeholder: will be updated)
9. Install Python dependencies in venv
10. Install Node.js dependencies
11. Download all models via python/download_models.py
12. Set up systemd service for FastAPI (auto-start on boot)
13. Configure firewall (allow SSH 22, API 8000)

Print summary at end:
- CUDA version
- GPU detected (nvidia-smi output)
- Disk usage of models/
- Service status

Make it idempotent (safe to run multiple times).

Usage: bash scripts/setup_droplet.sh
```

---

## **PROMPT 3: Model Downloader (All Local Models)**

```
Create a script to download and cache all required models.

FILE: python/download_models.py

Download these models to models/ directory:

1. Whisper large-v3
   - Use: openai/whisper-large-v3 from Hugging Face
   - Or: Download directly from OpenAI
   
2. Translation: facebook/nllb-200-3.3B
   - Supports Uzbek (uzb_Cyrl, uzb_Latn)
   - 3.3B parameter model (good quality, fits in 16GB GPU)

3. Emotion: j-hartmann/emotion-english-distilroberta-base
   - Small model (~250MB)

4. TTS: Coqui XTTS-v2
   - From: https://huggingface.co/coqui/XTTS-v2
   - Supports Uzbek (uz)

5. Wav2Lip checkpoint
   - From: https://github.com/Rudrabha/Wav2Lip
   - Download wav2lip_gan.pth

Script behavior:
- Check if model exists before downloading
- Show progress bars (use tqdm)
- Verify checksums (optional for MVP)
- Print disk space used
- Handle network errors gracefully

Run with: python download_models.py --model-dir ./models

Estimated total size: ~15-20GB (warn user before starting).
```

---

## **PROMPT 4: Audio Extraction (Same as Before)**

```
FILE: node/src/pipeline.js

Implement extractAudio(inputVideo, outputAudio):
1. Use fluent-ffmpeg
2. Extract as 16kHz mono WAV
3. Save to data/temp/original_audio.wav
4. Return { success: true, path: outputAudio, duration: X }

Add to node/src/config.js:
- INPUT_DIR = process.env.INPUT_DIR || 'data/input'
- OUTPUT_DIR = process.env.OUTPUT_DIR || 'data/output'
- TEMP_DIR = process.env.TEMP_DIR || 'data/temp'
- PYTHON_API = process.env.PYTHON_API || 'http://localhost:8000'

Error handling:
- Check if ffmpeg is installed
- Validate input file exists
- Create temp dir if missing
```

---

## **PROMPT 5: Local Whisper Transcription**

```
FILE: python/services/transcribe.py

Create POST /transcribe endpoint using local Whisper model.

Implementation:
import whisper
import torch

# Load model on startup (global variable)
device = "cuda" if torch.cuda.is_available() else "cpu"
model = whisper.load_model("large-v3", device=device, download_root="./models")

@app.post("/transcribe")
async def transcribe(file: UploadFile):
    # Save uploaded file temporarily
    temp_path = f"/tmp/{file.filename}"
    with open(temp_path, "wb") as f:
        f.write(await file.read())
    
    # Transcribe with word-level timestamps
    result = model.transcribe(
        temp_path,
        language="en",  # Auto-detect or specify
        word_timestamps=True,
        task="transcribe"
    )
    
    # Format segments
    segments = [
        {
            "id": i,
            "start": seg["start"],
            "end": seg["end"],
            "text": seg["text"].strip()
        }
        for i, seg in enumerate(result["segments"])
    ]
    
    os.remove(temp_path)
    
    return {"segments": segments, "language": result["language"]}

Requirements:
- Use GPU if available (check with nvidia-smi)
- Return timestamps in seconds (float)
- Strip whitespace from text
- Handle audio files up to 60 minutes

Add logging: Print "Transcription took X seconds" to console.
```

---

## **PROMPT 6: Local NLLB Translation (Replaces GPT-4)**

```
FILE: python/services/translate.py

Create POST /translate endpoint using Facebook NLLB model (local).

Implementation:
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
import torch

# Load model on startup
device = "cuda" if torch.cuda.is_available() else "cpu"
model_name = "facebook/nllb-200-3.3B"
tokenizer = AutoTokenizer.from_pretrained(model_name, cache_dir="./models")
model = AutoModelForSeq2SeqLM.from_pretrained(model_name, cache_dir="./models").to(device)

@app.post("/translate")
async def translate(request: dict):
    """
    Request: {
        "text": "Hello world",
        "source_lang": "eng_Latn",
        "target_lang": "uzb_Cyrl",  # Uzbek Cyrillic
        "emotion": "neutral"  # Used for context (future: adjust translation style)
    }
    """
    
    # Tokenize
    inputs = tokenizer(
        request["text"], 
        return_tensors="pt", 
        padding=True,
        src_lang=request.get("source_lang", "eng_Latn")
    ).to(device)
    
    # Translate
    translated_tokens = model.generate(
        **inputs,
        forced_bos_token_id=tokenizer.lang_code_to_id[request["target_lang"]],
        max_length=200
    )
    
    # Decode
    translation = tokenizer.batch_decode(translated_tokens, skip_special_tokens=True)[0]
    
    return {"translated_text": translation}

Notes:
- NLLB language codes: eng_Latn (English), uzb_Cyrl (Uzbek Cyrillic), uzb_Latn (Uzbek Latin)
- For MVP: Ignore emotion (NLLB doesn't support style transfer)
- Future: Fine-tune NLLB on emotional dialogue pairs

Add to requirements.txt: sentencepiece (required for NLLB tokenizer)
```

---

## **PROMPT 7: Emotion Detection (Same Logic)**

```
FILE: python/services/emotion.py

POST /detect_emotion endpoint (unchanged from original prompts).

Use: j-hartmann/emotion-english-distilroberta-base

Return emotions: neutral, joy, sadness, anger, fear, surprise

This is already local - no changes needed from original PROMPT 5.
```

---

## **PROMPT 8: Voice Cloning with Coqui XTTS (Local)**

```
FILE: python/services/tts.py

POST /generate_speech endpoint using local XTTS model.

Implementation:
from TTS.api import TTS
import torch

device = "cuda" if torch.cuda.is_available() else "cpu"
tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2", gpu=(device=="cuda"))

@app.post("/generate_speech")
async def generate_speech(request: dict):
    """
    Request: {
        "text": "Salom dunyo",
        "reference_audio": "path/to/voice_sample.wav",
        "language": "uz",
        "output_path": "data/temp/segment_0.wav",
        "emotion": "joy"  # Currently unused by XTTS
    }
    """
    
    # Generate speech
    tts.tts_to_file(
        text=request["text"],
        speaker_wav=request["reference_audio"],
        language=request["language"],
        file_path=request["output_path"]
    )
    
    # Get audio duration
    import soundfile as sf
    audio, sr = sf.read(request["output_path"])
    duration = len(audio) / sr
    
    return {"success": True, "duration": duration}

Requirements:
- Extract 5-10 second reference audio from original video (first dialogue segment)
- Use same reference for all segments (for consistency)
- XTTS supports Uzbek natively (language code: "uz")

Add to requirements.txt: soundfile, TTS

Note: XTTS emotion control is limited - rely on text + reference audio quality.
```

---

## **PROMPT 9: Node.js Pipeline Integration (Updated for Local Models)**

```
FILE: node/src/pipeline.js

Update translateSegments() function:
- Remove OpenAI API call
- Call POST http://localhost:8000/translate
- Pass: { text, source_lang: "eng_Latn", target_lang: "uzb_Cyrl", emotion }
- Store translated_text in segment

Update generateDubbedAudio() function:
- Extract reference audio: First 10 seconds of original audio
- For each segment:
  - Call /generate_speech with reference_audio path
  - Use language: "uz"
  - Save to data/temp/segment_{id}.wav

No API keys needed - everything runs locally!

Add progress logging:
console.log(`Processing segment ${i+1}/${total}...`);
```

---

## **PROMPT 10-15: Same as Original (Wav2Lip, Assembly, Testing)**

Use original PROMPT 10-15 with these tweaks:

**PROMPT 10 (Wav2Lip)**: No changes  
**PROMPT 11 (Assembly)**: No changes  
**PROMPT 12 (Orchestrator)**: Add `--cloud` flag to skip local file validation  
**PROMPT 13 (Startup)**: Add systemd service for auto-restart  
**PROMPT 14 (Testing)**: Download test video with `yt-dlp` on droplet  
**PROMPT 15 (Docs)**: Add DigitalOcean deployment instructions  

---

## **PROMPT 16: DigitalOcean Deployment Workflow**

```
Create deployment and usage scripts for cloud GPU workflow.

FILE: scripts/deploy.sh
#!/bin/bash
# Run this on your LOCAL machine to deploy to DigitalOcean

DROPLET_IP="your-droplet-ip"
REPO_URL="https://github.com/yourusername/dubbing-mvp.git"

echo "Deploying to $DROPLET_IP..."

ssh root@$DROPLET_IP << 'EOF'
  cd /root/dubbing-mvp
  git pull origin main
  cd python && source venv/bin/activate && pip install -r requirements.txt
  cd ../node && npm install
  sudo systemctl restart dubbing-api
  echo "Deployment complete!"
EOF

FILE: scripts/process_video.sh
#!/bin/bash
# Run this on DigitalOcean droplet to process a video

INPUT_VIDEO=$1

if [ -z "$INPUT_VIDEO" ]; then
  echo "Usage: ./process_video.sh path/to/video.mp4"
  exit 1
fi

echo "Starting dubbing pipeline..."
cd /root/dubbing-mvp/node
node src/index.js --input "$INPUT_VIDEO" --output data/output/dubbed.mp4

echo "Done! Download from: /root/dubbing-mvp/data/output/dubbed.mp4"

FILE: README.md (add section)
## Deployment to DigitalOcean

1. Create GPU Droplet (H100 or A100)
2. SSH into droplet: ssh root@your-ip
3. Run setup: bash scripts/setup_droplet.sh (takes 20-30 min)
4. Upload test video: scp test.mp4 root@your-ip:/root/dubbing-mvp/data/input/
5. Process: ssh root@your-ip "bash /root/dubbing-mvp/scripts/process_video.sh data/input/test.mp4"
6. Download result: scp root@your-ip:/root/dubbing-mvp/data/output/dubbed.mp4 ./

Estimated cost: $2-3 per hour (turn off droplet when not testing!)
```

---

## **PROMPT 17: Cost Optimization & Monitoring**

```
Add cost tracking and auto-shutdown features.

FILE: scripts/auto_shutdown.sh
#!/bin/bash
# Add to cron: @hourly /root/dubbing-mvp/scripts/auto_shutdown.sh

# Check if any processes are running
if pgrep -f "node src/index.js" > /dev/null; then
  echo "Pipeline active, not shutting down"
  exit 0
fi

# Check last activity (file modification in data/temp)
LAST_ACTIVITY=$(find /root/dubbing-mvp/data/temp -type f -mmin -60 | wc -l)

if [ "$LAST_ACTIVITY" -eq 0 ]; then
  echo "No activity in 60 min, shutting down droplet"
  # Uncomment to enable:
  # shutdown -h now
fi

FILE: python/app.py (add endpoint)
@app.get("/stats")
async def get_stats():
    """Monitor GPU usage and costs"""
    import subprocess
    
    # Get GPU stats
    gpu_info = subprocess.check_output(["nvidia-smi", "--query-gpu=utilization.gpu,memory.used", "--format=csv,noheader,nounits"]).decode()
    
    # Estimate cost (DigitalOcean H100 = $2.50/hour)
    uptime = subprocess.check_output(["uptime", "-p"]).decode()
    
    return {
        "gpu_usage": gpu_info.strip(),
        "uptime": uptime.strip(),
        "estimated_cost_usd": "Calculate based on uptime"
    }

Add to README:
- Always shut down droplet after testing!
- Check costs: doctl compute droplet list
- Auto-shutdown cron job included (edit scripts/auto_shutdown.sh to enable)
```

---

## **Final Checklist for 1-Week MVP**

### **Week 1 Goals** (Bare-bones)
- [ ] Setup DigitalOcean droplet with GPU
- [ ] Install all models (run download_models.py)
- [ ] Test Whisper transcription on 1-min clip
- [ ] Test NLLB translation (English → Uzbek)
- [ ] Test XTTS voice cloning with sample audio
- [ ] Run full pipeline on 1-min test video
- [ ] Verify output quality (watch dubbed video)

### **Week 2 Goals** (Polish)
- [ ] CLI arguments (`--input`, `--output`, `--language`)
- [ ] Error handling + retry logic
- [ ] Parallel segment processing
- [ ] Audio alignment improvements
- [ ] Wav2Lip integration
- [ ] Cost tracking dashboard
- [ ] Demo video for GitHub README

---

## **Immediate Next Steps**

1. **Paste PROMPT 1** into Cursor → Generate project structure
2. **Create DigitalOcean GPU Droplet** (H100 or A100)
3. **Paste PROMPT 2** into Cursor → Generate setup script
4. **SSH into droplet** → Run `bash scripts/setup_droplet.sh`
5. **Paste PROMPTS 3-9** sequentially → Build pipeline
6. **Upload test video** → Run first end-to-end test

---

## **Questions?**

- Should I generate the **systemd service file** for auto-starting FastAPI?
- Do you want a **Jupyter notebook** for interactive testing on the droplet?
- Should I add **Telegram bot integration** for remote video processing? (upload video → get dubbed result)

Let me know and I'll add those prompts! 🚀