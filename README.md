# MoneyPrint Junior — Audio to Image

Local-first Windows 11 app that turns WAV/MP3/M4A audio into a chronological AI storyboard.

## Pipeline

`Audio → FFprobe → faster-whisper → Ollama qwen3:8b → semantic scenes → local ComfyUI → storyboard`

SonicDiffusion and Sound2Scene/Sound2Vision are optional experimental adapters. They are never reported as active unless their runtime/checkpoints are actually available.

## Windows / AMD

This project does **not** assume CUDA and never silently moves a huge image model to CPU. The recommended production image path is a local ComfyUI installation configured for your AMD Windows system.

Ollama stays on Windows at `http://localhost:11434`. Docker uses `http://host.docker.internal:11434`.

## Start

```bat
INSTALL.bat
START.bat
```

UI: http://localhost:5173  
API docs: http://localhost:8000/docs

Set your ComfyUI checkpoint filename in the UI before image generation.

## Storage

```text
storage/projects/<project-id>/
  source_audio/
  transcript.json
  storyboard.json
  timeline.json
  scenes/scene_001/
    audio.wav
    prompt.json
    image_001.png
  exports/
```

## Experimental engines

`backend/app/adapters/sonic_diffusion.py` and `backend/app/adapters/sound2scene.py` keep older research stacks isolated from the production environment.

## Tests

```bat
TEST.bat
```

Tests only print PASS when commands actually execute successfully.
