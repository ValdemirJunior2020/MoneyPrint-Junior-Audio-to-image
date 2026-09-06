from pathlib import Path
from ..config import settings

UNAVAILABLE = "Sound2Scene/Sound2Vision unavailable — using transcript + Ollama visual planning."

def status() -> dict:
    root = Path(settings.sound2scene_path)
    has_code = (root / "test.py").exists() or (root / "test_sound2vision.py").exists()
    available = has_code and (root / "checkpoints").exists()
    return {
        "name": "Sound2Scene/Sound2Vision",
        "available": available,
        "mode": "experimental" if available else "adapter-only",
        "message": "Upstream code/checkpoint directory detected." if available else UNAVAILABLE,
        "path": str(root)
    }

def generate(*args, **kwargs):
    if not status()["available"]:
        raise RuntimeError(UNAVAILABLE)
    raise RuntimeError("Sound2Scene/Sound2Vision detected but remains isolated because upstream targets older CUDA/PyTorch stacks.")
