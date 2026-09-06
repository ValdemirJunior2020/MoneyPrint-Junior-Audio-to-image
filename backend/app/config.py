from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "qwen3:8b"
    comfyui_url: str = "http://127.0.0.1:8188"
    comfyui_checkpoint: str = ""
    whisper_model: str = "medium"
    whisper_device: str = "auto"
    whisper_compute_type: str = "auto"
    storage_root: str = "storage/projects"
    sonic_diffusion_path: str = "backend/experimental/SonicDiffusion"
    sound2scene_path: str = "backend/experimental/Sound2Scene"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def storage_path(self) -> Path:
        p = Path(self.storage_root)
        p.mkdir(parents=True, exist_ok=True)
        return p

settings = Settings()
