w# Movie Dubbing Pipeline

A complete video dubbing pipeline that translates English videos to Uzbek using local ML models. The system transcribes audio, translates text, detects emotions, generates voice-cloned speech, and syncs lip movements - all running locally without API costs.

## Features![1766660648910](image/README/1766660648910.png)![1766660662065](image/README/1766660662065.png)

- **Local Processing**: All models run locally (no API costs)
- **GPU Support**: Optimized for CUDA-enabled GPUs with CPU fallback
- **Complete Pipeline**: Transcription → Translation → Emotion Detection → TTS → Lip-Sync
- **Voice Cloning**: Uses Coqui XTTS v2 for natural-sounding voice cloning
- **Cloud Ready**: Deploy to DigitalOcean GPU Droplets for production

## Architecture

```
┌─────────────┐
│  Video File │
└──────┬──────┘
       │
       ▼
┌─────────────────┐     ┌──────────────┐
│  Node.js CLI    │────▶│  FastAPI     │
│  Orchestrator   │     │  Services    │
└─────────────────┘     └──────────────┘
       │                        │
       │                        ▼
       │              ┌──────────────────┐
       │              │  ML Models       │
       │              │  - Whisper       │
       │              │  - NLLB          │
       │              │  - Emotion       │
       │              │  - XTTS          │
       │              │  - Wav2Lip       │
       │              └──────────────────┘
       │
       ▼
┌─────────────┐
│ Dubbed Video│
└─────────────┘
```

## Project Structure

```
dubbing-mvp/
├── node/                 # Node.js orchestration
│   ├── src/
│   │   ├── index.js      # CLI entry point
│   │   ├── pipeline.js   # Pipeline orchestrator
│   │   ├── config.js     # Configuration
│   │   └── utils.js      # Utilities
│   └── package.json
├── python/               # Python ML services
│   ├── app.py            # FastAPI server
│   ├── download_models.py
│   └── services/         # ML service endpoints
├── data/
│   ├── input/            # Input videos
│   ├── output/           # Final results
│   └── temp/             # Temporary files
├── models/               # Model cache (gitignored)
├── scripts/              # Deployment scripts
└── docker/               # Docker configuration
```

## Prerequisites

### Local Development

- **Python 3.10+**
- **Node.js 20.x**
- **FFmpeg** (with GPU support optional)
- **CUDA 12.1+** (optional, for GPU acceleration)
- **15-20 GB disk space** (for models)

### Cloud Deployment

- **DigitalOcean GPU Droplet** (H100, A100, or RTX-enabled)
- **Ubuntu 22.04**
- **SSH access**

## Installation

### 1. Clone Repository

```bash
git clone <your-repo-url> dubbing-mvp
cd dubbing-mvp
```

### 2. Install Python Dependencies

```bash
cd python
python3.10 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Install Node.js Dependencies

```bash
cd ../node
npm install
```

### 4. Download Models

```bash
cd ../python
source venv/bin/activate
python download_models.py --model-dir ../models
```

This will download:
- Whisper large-v3 (~3 GB)
- NLLB-200-3.3B (~6.6 GB)
- Emotion model (~250 MB)
- Coqui XTTS-v2 (~1.8 GB)
- Wav2Lip checkpoint (~400 MB)

**Total: ~15-20 GB**

### 5. Configure Environment

Copy `.env.example` to `.env` and adjust settings:

```bash
cp .env.example .env
```

## Usage

### Start the API Server

```bash
cd python
source venv/bin/activate
python app.py
```

The API will be available at `http://localhost:8000`

### Process a Video

```bash
cd node
node src/index.js -i ../data/input/video.mp4 -o ../data/output/dubbed.mp4
```

### CLI Options

```bash
node src/index.js [options]

Options:
  -i, --input <path>     Input video file (required)
  -o, --output <path>    Output video file (optional)
  -l, --language <code>  Target language: uzb_Latn (default) or uzb_Cyrl
  --cloud                Skip local file validation
  -h, --help             Show help
```

## API Endpoints

### Health Check
```bash
GET /health
```

### Transcription
```bash
POST /transcribe
Content-Type: multipart/form-data
Body: file (audio file)
```

### Translation
```bash
POST /translate
Content-Type: application/json
Body: {
  "text": "Hello world",
  "source_lang": "eng_Latn",
  "target_lang": "uzb_Latn",
  "emotion": "neutral"
}
```

### Emotion Detection
```bash
POST /emotion
Content-Type: application/json
Body: {
  "text": "I am happy!"
}
```

### Text-to-Speech
```bash
POST /tts
Content-Type: application/json
Body: {
  "text": "Salom dunyo",
  "reference_audio": "path/to/voice.wav",
  "language": "uz",
  "output_path": "output.wav"
}
```

### Lip-Sync
```bash
POST /lipsync
Content-Type: application/json
Body: {
  "video_path": "input.mp4",
  "audio_path": "audio.wav",
  "output_path": "output.mp4"
}
```

### Statistics
```bash
GET /stats
```

## Cloud Deployment (DigitalOcean)

### 1. Create GPU Droplet

- Choose GPU-enabled droplet (H100, A100, or RTX)
- Select Ubuntu 22.04
- Note the IP address

### 2. Run Setup Script

```bash
ssh root@your-droplet-ip
# On the droplet:
git clone <your-repo-url> /root/dubbing-mvp
cd /root/dubbing-mvp
bash scripts/setup_droplet.sh
```

### 3. Download Models

```bash
cd /root/dubbing-mvp/python
source venv/bin/activate
python download_models.py --model-dir ../models
```

### 4. Start API Service

**Option A: Manual**
```bash
cd /root/dubbing-mvp/python
source venv/bin/activate
python app.py
```

**Option B: Systemd Service**
```bash
sudo cp scripts/dubbing-api.service /etc/systemd/system/
sudo systemctl enable dubbing-api
sudo systemctl start dubbing-api
```

### 5. Process Videos

```bash
# Upload video
scp video.mp4 root@your-ip:/root/dubbing-mvp/data/input/

# Process
ssh root@your-ip "cd /root/dubbing-mvp && bash scripts/process_video.sh data/input/video.mp4"

# Download result
scp root@your-ip:/root/dubbing-mvp/data/output/video_dubbed.mp4 ./
```

### 6. Deploy Updates

From your local machine:

```bash
DROPLET_IP=your-ip bash scripts/deploy.sh
```

## Docker Deployment

### Build and Run

```bash
cd docker
docker-compose build
docker-compose up -d
```

### GPU Support

Requires `nvidia-docker2`:

```bash
# Install nvidia-docker2
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list
sudo apt-get update && sudo apt-get install -y nvidia-docker2
sudo systemctl restart docker
```

## Cost Optimization

### Auto-Shutdown Script

The `scripts/auto_shutdown.sh` script monitors activity and shuts down the droplet when idle:

```bash
# Add to crontab
crontab -e
# Add: @hourly /root/dubbing-mvp/scripts/auto_shutdown.sh
```

**Important**: Uncomment the `shutdown -h now` line in the script to enable auto-shutdown.

### Cost Tracking

Check droplet costs:
```bash
doctl compute droplet list
```

Monitor GPU usage:
```bash
curl http://localhost:8000/stats
```

## Testing

### Test Individual Services

```bash
bash scripts/test_services.sh
```

### Test Full Pipeline

```bash
# Download test video
pip install yt-dlp
yt-dlp -o data/input/test.mp4 'https://youtube.com/watch?v=VIDEO_ID'

# Run test
bash scripts/test_pipeline.sh data/input/test.mp4
```

## Troubleshooting

### API Not Starting

- Check if port 8000 is available: `lsof -i :8000`
- Verify Python dependencies: `pip list`
- Check logs for errors

### Models Not Loading

- Verify models are downloaded: `ls -lh models/`
- Check disk space: `df -h`
- Re-download models: `python download_models.py --force`

### GPU Not Detected

- Check CUDA: `nvidia-smi`
- Verify PyTorch CUDA: `python -c "import torch; print(torch.cuda.is_available())"`
- Set `CUDA_VISIBLE_DEVICES=0` in `.env`

### FFmpeg Errors

- Install FFmpeg: `apt install ffmpeg` (Linux) or `brew install ffmpeg` (Mac)
- Verify installation: `ffmpeg -version`

### Translation Quality Issues

- Try different language codes: `uzb_Cyrl` vs `uzb_Latn`
- Adjust translation parameters in `services/translate.py`
- Consider fine-tuning NLLB model for your domain

## Performance Tips

1. **Use GPU**: Processing is 10-50x faster on GPU
2. **Batch Processing**: Process multiple videos in parallel
3. **Model Caching**: Models are cached after first load
4. **Temp Cleanup**: Regularly clean `data/temp/` directory
5. **SSD Storage**: Use SSD for faster I/O

## Language Support

Currently supports:
- **Source**: English (eng_Latn)
- **Target**: Uzbek Latin (uzb_Latn) - default, or Uzbek Cyrillic (uzb_Cyrl)

To add more languages:
1. Update `config.js` with new language codes
2. Verify NLLB supports the language
3. Check XTTS language support

## License

MIT License

## Contributing

Contributions welcome! Please open an issue or submit a pull request.

## Support

For issues and questions:
- Open an issue on GitHub
- Check the troubleshooting section
- Review API logs: `journalctl -u dubbing-api -f`

## Roadmap

- [ ] Support for more languages
- [ ] Real-time processing
- [ ] Web UI
- [ ] Batch processing API
- [ ] Advanced lip-sync with Wav2Lip full implementation
- [ ] Emotion-aware translation
- [ ] Quality metrics and evaluation

# movie-dubbing-pipeline
