# Testing Guide

Complete guide for testing the dubbing pipeline project.

## Prerequisites

Before testing, ensure you have:

1. **Python 3.10+** installed
2. **Node.js 20.x** installed
3. **FFmpeg** installed
4. **Dependencies installed** (see below)
5. **Models downloaded** (optional for quick tests, required for full pipeline)

## Step 1: Install Dependencies

### Python Dependencies

```bash
cd python
python -m venv venv

# On Windows:
venv\Scripts\activate

# On Linux/Mac:
source venv/bin/activate

pip install -r requirements.txt
```

### Node.js Dependencies

```bash
cd node
npm install
```

## Step 2: Download Models (Optional for Quick Tests)

For quick API tests, you can skip model downloads. For full pipeline testing, download models:

```bash
cd python
source venv/bin/activate  # or venv\Scripts\activate on Windows
python download_models.py --model-dir ../models
```

**Note**: This downloads ~15-20 GB of models. You can test individual endpoints without all models.

## Step 3: Start the API Server

```bash
cd python
source venv/bin/activate  # or venv\Scripts\activate on Windows
python app.py
```

The API should start on `http://localhost:8000`

Verify it's running:
```bash
curl http://localhost:8000/health
```

Or open in browser: http://localhost:8000/health

## Step 4: Test Individual Services

### Option A: Using Test Script (Linux/Mac)

```bash
bash scripts/test_services.sh
```

### Option B: Manual Testing

#### 1. Health Check

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "device": "cuda" or "cpu",
  "models_loaded": ["whisper", "translate", "emotion", "tts", "lipsync"]
}
```

#### 2. Translation Test

```bash
curl -X POST http://localhost:8000/translate \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello, how are you?",
    "source_lang": "eng_Latn",
    "target_lang": "uzb_Latn"
  }'
```

Expected response:
```json
{
  "translated_text": "Salom, qandaysiz?",
  "source_lang": "eng_Latn",
  "target_lang": "uzb_Latn",
  "original_text": "Hello, how are you?"
}
```

#### 3. Emotion Detection Test

```bash
curl -X POST http://localhost:8000/emotion \
  -H "Content-Type: application/json" \
  -d '{
    "text": "I am so happy today!"
  }'
```

Expected response:
```json
{
  "emotion": "joy",
  "confidence": 0.95,
  "scores": {
    "neutral": 0.01,
    "joy": 0.95,
    "sadness": 0.02,
    ...
  }
}
```

#### 4. Transcription Test (Requires Audio File)

First, extract audio from a video or use a sample audio file:

```bash
# Extract audio from video
ffmpeg -i video.mp4 -ar 16000 -ac 1 audio.wav

# Test transcription
curl -X POST http://localhost:8000/transcribe \
  -F "file=@audio.wav"
```

#### 5. Stats Endpoint

```bash
curl http://localhost:8000/stats
```

## Step 5: Test Full Pipeline

### Option A: Using Test Script (Linux/Mac)

1. **Get a test video** (or use your own):

```bash
# Install yt-dlp if needed
pip install yt-dlp

# Download a short test video (30-60 seconds recommended)
yt-dlp -o data/input/test.mp4 'https://youtube.com/watch?v=VIDEO_ID'
```

2. **Run the test script**:

```bash
bash scripts/test_pipeline.sh data/input/test.mp4
```

### Option B: Manual Pipeline Test

1. **Prepare a test video**:
   - Place a short video (30-60 seconds) in `data/input/`
   - Recommended: English speech, clear audio

2. **Run the pipeline**:

```bash
cd node
node src/index.js -i ../data/input/test.mp4 -o ../data/output/test_dubbed.mp4
```

3. **Check the output**:
   - Output will be in `data/output/test_dubbed.mp4`
   - Play the video to verify dubbing quality

## Step 6: Windows-Specific Testing

### Using PowerShell

1. **Start API** (PowerShell):
```powershell
cd python
.\venv\Scripts\Activate.ps1
python app.py
```

2. **Test endpoints** (PowerShell):
```powershell
# Health check
Invoke-WebRequest -Uri http://localhost:8000/health | Select-Object -ExpandProperty Content

# Translation test
$body = @{
    text = "Hello, how are you?"
    source_lang = "eng_Latn"
    target_lang = "uzb_Latn"
} | ConvertTo-Json

Invoke-WebRequest -Uri http://localhost:8000/translate -Method POST -Body $body -ContentType "application/json" | Select-Object -ExpandProperty Content
```

3. **Run pipeline** (PowerShell):
```powershell
cd node
node src/index.js -i ..\data\input\test.mp4 -o ..\data\output\test_dubbed.mp4
```

## Testing Checklist

### Quick Smoke Tests (No Models Required)
- [ ] API server starts without errors
- [ ] Health endpoint returns 200
- [ ] Stats endpoint returns system info

### Service Tests (Requires Models)
- [ ] Translation endpoint works
- [ ] Emotion detection endpoint works
- [ ] Transcription endpoint works (with audio file)
- [ ] TTS endpoint works (with reference audio)
- [ ] Lip-sync endpoint works (basic audio replacement)

### Full Pipeline Test
- [ ] Audio extraction works
- [ ] Transcription produces segments
- [ ] Translation produces Uzbek text
- [ ] TTS generates audio files
- [ ] Final video is created
- [ ] Output video plays correctly

## Troubleshooting

### API Won't Start

**Error**: `ModuleNotFoundError` or import errors
- **Solution**: Make sure virtual environment is activated and dependencies are installed
  ```bash
  cd python
  source venv/bin/activate
  pip install -r requirements.txt
  ```

**Error**: `Port 8000 already in use`
- **Solution**: Change port in `.env` or kill the process using port 8000
  ```bash
  # Find process
  lsof -i :8000  # Linux/Mac
  netstat -ano | findstr :8000  # Windows
  
  # Kill process or change port
  ```

### Models Not Loading

**Error**: `Model not found` or `Checkpoint not found`
- **Solution**: Download models first
  ```bash
  python download_models.py --model-dir ../models
  ```

**Error**: `CUDA out of memory`
- **Solution**: Use CPU mode or reduce batch size
  ```bash
  # Set in .env
  CUDA_VISIBLE_DEVICES=""
  ```

### Pipeline Errors

**Error**: `API is not running`
- **Solution**: Start the API server first
  ```bash
  cd python && source venv/bin/activate && python app.py
  ```

**Error**: `FFmpeg not found`
- **Solution**: Install FFmpeg
  ```bash
  # Windows: Download from https://ffmpeg.org/download.html
  # Linux: sudo apt install ffmpeg
  # Mac: brew install ffmpeg
  ```

**Error**: `File not found`
- **Solution**: Check file paths are correct and files exist
  ```bash
  ls -la data/input/  # Verify input file exists
  ```

### Translation Quality Issues

- Try different language codes: `uzb_Cyrl` vs `uzb_Latn`
- Check if source text is clear English
- Verify NLLB model loaded correctly

### TTS Quality Issues

- Ensure reference audio is clear (first 10 seconds of original)
- Check audio format (should be WAV, 16kHz, mono)
- Verify XTTS model loaded correctly

## Performance Testing

### Measure Processing Time

```bash
# Time the full pipeline
time node src/index.js -i input.mp4 -o output.mp4

# Check API response times
curl -w "@curl-format.txt" -o /dev/null -s http://localhost:8000/health
```

### GPU vs CPU Comparison

1. **With GPU**:
   ```bash
   CUDA_VISIBLE_DEVICES=0 python app.py
   ```

2. **CPU only**:
   ```bash
   CUDA_VISIBLE_DEVICES="" python app.py
   ```

Compare processing times for same video.

## Sample Test Videos

For testing, use short videos (30-60 seconds) with:
- Clear English speech
- Good audio quality
- Single speaker (for voice cloning)
- Minimal background noise

## Next Steps

After successful testing:
1. Process longer videos
2. Test with different languages
3. Optimize for your use case
4. Deploy to cloud (DigitalOcean)

## Getting Help

If tests fail:
1. Check API logs for errors
2. Verify all dependencies are installed
3. Ensure models are downloaded
4. Check file permissions
5. Review troubleshooting section above

