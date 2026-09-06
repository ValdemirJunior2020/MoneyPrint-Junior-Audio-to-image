from typing import Literal
from pydantic import BaseModel, Field, model_validator

Aspect = Literal["16:9", "9:16", "1:1"]
Style = Literal["Photorealistic","Cinematic","Documentary","Historical","Biblical","Classical Painting","Illustration","Dark Dramatic","Inspirational"]

class AudioScene(BaseModel):
    scene_number: int = Field(ge=1)
    start_seconds: float = Field(ge=0)
    end_seconds: float = Field(gt=0)
    transcript: str = ""
    sound_description: str | None = None
    visual_description: str
    image_prompt: str
    negative_prompt: str = ""
    historical_context: str | None = None
    importance: int = Field(default=5, ge=1, le=10)
    image_count: int = Field(default=1, ge=1, le=6)

    @model_validator(mode="after")
    def valid_times(self):
        if self.end_seconds <= self.start_seconds:
            raise ValueError("end_seconds must be greater than start_seconds")
        return self

class AudioStoryboard(BaseModel):
    title: str
    audio_duration: float = Field(gt=0)
    scenes: list[AudioScene]

    @model_validator(mode="after")
    def valid_order(self):
        last = -1.0
        for i, scene in enumerate(self.scenes, 1):
            if scene.scene_number != i:
                raise ValueError("scene numbers must be sequential")
            if scene.start_seconds < last - 0.05:
                raise ValueError("scenes must be chronological")
            if scene.end_seconds > self.audio_duration + 1.0:
                raise ValueError("scene exceeds audio duration")
            last = scene.end_seconds
        return self

class GenerationOptions(BaseModel):
    aspect: Aspect = "16:9"
    style: Style = "Cinematic"
    min_scene_seconds: float = Field(default=5, ge=2, le=60)
    max_scene_seconds: float = Field(default=12, ge=3, le=120)
    images_per_scene: int = Field(default=1, ge=1, le=6)
    automatic_image_count: bool = True
    historical_accuracy: bool = True
    seed: int = 42
    steps: int = Field(default=24, ge=1, le=100)
    cfg: float = Field(default=6.5, ge=1, le=20)
    quality: Literal["Draft","Standard","High"] = "Standard"
    image_engine: Literal["comfyui","sonicdiffusion","sound2scene"] = "comfyui"
    checkpoint: str = ""

class ProjectStatus(BaseModel):
    project_id: str
    stage: str
    detail: str = ""
    progress: float = Field(default=0, ge=0, le=1)
    cancelled: bool = False
