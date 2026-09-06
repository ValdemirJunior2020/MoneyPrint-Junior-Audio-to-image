from pathlib import Path
from ..config import settings

UNAVAILABLE = "Audio-conditioned engine unavailable — using transcript + Ollama visual planning."

def status() -> dict:
    root = Path(settings.sonic_diffusion_path)
    available = (root / "pipeline_stable_diffusion_custom.py").exists() and (root / "CLAP").exists() and (root / "ckpts").exists()
    return {
        "name": "SonicDiffusion",
        "available": available,
        "mode": "experimental-audio-conditioned" if available else "adapter-only",
        "message": "SonicDiffusion files/checkpoints detected." if available else UNAVAILABLE,
        "path": str(root)
    }

def generate(*args, **kwargs):
    if not status()["available"]:
        raise RuntimeError(UNAVAILABLE)
    raise RuntimeError("SonicDiffusion detected but isolated execution must be validated for this machine before activation.")
