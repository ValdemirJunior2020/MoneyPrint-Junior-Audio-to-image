from __future__ import annotations
import asyncio
import json
import re
import subprocess
import uuid
import zipfile
from pathlib import Path
from typing import Any

import httpx
from faster_whisper import WhisperModel

from .config import settings
from .models import AudioScene, AudioStoryboard, GenerationOptions

WHISPER: WhisperModel | None = None

def safe_project_id(value: str) -> str:
    if not re.fullmatch(r"[a-f0-9\\-]{8,64}", value):
        raise ValueError("invalid project id")
    return value

def probe_duration(path: Path) -> float:
    out = subprocess.check_output(["ffprobe","-v","error","-show_entries","format=duration","-of","default=noprint_wrappers=1:nokey=1",str(path)],text=True,stderr=subprocess.STDOUT).strip()
    return float(out)

def extract_scene_audio(source: Path, target: Path, start: float, end: float) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg","-y","-ss",str(start),"-to",str(end),"-i",str(source),"-ac","1","-ar","48000",str(target)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)

def whisper_runtime() -> tuple[str, str]:
    device = settings.whisper_device
    compute = settings.whisper_compute_type
    if device == "auto":
        return "cpu", "int8" if compute == "auto" else compute
    return device, "float16" if compute == "auto" else compute

def transcribe(path: Path) -> dict[str, Any]:
    global WHISPER
    device, compute = whisper_runtime()
    if WHISPER is None:
        WHISPER = WhisperModel(settings.whisper_model, device=device, compute_type=compute)
    segments, info = WHISPER.transcribe(str(path), vad_filter=True, beam_size=5)
    items = [{"start":round(s.start,3),"end":round(s.end,3),"text":s.text.strip()} for s in segments]
    return {"language":info.language,"language_probability":info.language_probability,"device":device,"compute_type":compute,"segments":items}

async def ollama_json(system_prompt: str, payload: dict[str, Any]) -> dict[str, Any]:
    body = {"model":settings.ollama_model,"format":"json","stream":False,"messages":[{"role":"system","content":system_prompt},{"role":"user","content":json.dumps(payload,ensure_ascii=False)}],"options":{"temperature":0.2}}
    async with httpx.AsyncClient(timeout=600) as client:
        r = await client.post(f"{settings.ollama_url.rstrip('/')}/api/chat", json=body)
        r.raise_for_status()
        return json.loads(r.json()["message"]["content"])

def fallback_storyboard(transcript: dict[str, Any], duration: float, options: GenerationOptions) -> AudioStoryboard:
    scenes: list[AudioScene] = []
    chunk: list[dict[str, Any]] = []
    start = 0.0
    n = 1
    for seg in transcript.get("segments", []):
        if not chunk: start = seg["start"]
        chunk.append(seg)
        if seg["end"] - start >= options.max_scene_seconds:
            text = " ".join(x["text"] for x in chunk)
            scenes.append(AudioScene(scene_number=n,start_seconds=start,end_seconds=seg["end"],transcript=text,visual_description=f"Visual scene representing: {text}",image_prompt=f"{options.style}, chronological documentary visual, {text}",negative_prompt="text, watermark, logo, modern anachronisms",image_count=options.images_per_scene))
            n += 1
            chunk = []
    if chunk:
        text = " ".join(x["text"] for x in chunk)
        end = min(duration, chunk[-1]["end"])
        scenes.append(AudioScene(scene_number=n,start_seconds=start,end_seconds=max(end,start+0.1),transcript=text,visual_description=f"Visual scene representing: {text}",image_prompt=f"{options.style}, chronological documentary visual, {text}",negative_prompt="text, watermark, logo, modern anachronisms",image_count=options.images_per_scene))
    if not scenes:
        scenes = [AudioScene(scene_number=1,start_seconds=0,end_seconds=max(duration,0.1),transcript="",sound_description="No speech detected",visual_description="Atmospheric scene matching the supplied audio",image_prompt=f"{options.style}, atmospheric cinematic scene matching the supplied audio",negative_prompt="text, watermark, logo",image_count=options.images_per_scene)]
    return AudioStoryboard(title="Audio Storyboard",audio_duration=duration,scenes=scenes)

async def plan_storyboard(transcript: dict[str, Any], duration: float, options: GenerationOptions) -> AudioStoryboard:
    accuracy = "Historical Accuracy ON: avoid modern clothing, cars, skyscrapers, modern weapons, wrong eras and random fantasy armor. For Bible/history use accurate geography, architecture, clothing, archaeology and landscapes." if options.historical_accuracy else "Historical Accuracy OFF."
    system_prompt = f"""You are a visual director building a chronological audio-to-image storyboard.
Return only valid JSON. Use semantic scene boundaries, not fixed intervals.
Target about {options.min_scene_seconds}-{options.max_scene_seconds} seconds unless story meaning requires a different boundary.
Split on changes in subject, location, person, event, sentence transition, emotional tone or important sound.
Never invent transcript text. Style: {options.style}. {accuracy}
Every scene needs scene_number, start_seconds, end_seconds, transcript, sound_description, visual_description,
image_prompt, negative_prompt, historical_context, importance and image_count."""
    payload = {"audio_duration":duration,"transcript":transcript,"options":options.model_dump(),"required_shape":{"title":"string","audio_duration":duration,"scenes":[{"scene_number":1,"start_seconds":0.0,"end_seconds":8.0,"transcript":"exact excerpt","sound_description":"optional","visual_description":"visual","image_prompt":"prompt","negative_prompt":"negative","historical_context":"optional","importance":5,"image_count":1}]}}
    try:
        data = await ollama_json(system_prompt, payload)
        data["audio_duration"] = duration
        for i, scene in enumerate(data.get("scenes", []), 1):
            scene["scene_number"] = i
            if not options.automatic_image_count: scene["image_count"] = options.images_per_scene
        return AudioStoryboard.model_validate(data)
    except Exception:
        return fallback_storyboard(transcript, duration, options)

def aspect_size(aspect: str, quality: str) -> tuple[int,int]:
    return {"Draft":{"16:9":(768,432),"9:16":(432,768),"1:1":(512,512)},"Standard":{"16:9":(1024,576),"9:16":(576,1024),"1:1":(768,768)},"High":{"16:9":(1344,768),"9:16":(768,1344),"1:1":(1024,1024)}}[quality][aspect]

async def comfy_generate(prompt: str, negative: str, options: GenerationOptions, out_path: Path, seed: int):
    checkpoint = options.checkpoint or settings.comfyui_checkpoint
    if not checkpoint: raise RuntimeError("ComfyUI checkpoint is not configured")
    workflow = json.loads(Path("backend/workflows/comfy_text_to_image.json").read_text(encoding="utf-8"))
    width, height = aspect_size(options.aspect, options.quality)
    workflow["4"]["inputs"]["ckpt_name"] = checkpoint
    workflow["6"]["inputs"]["text"] = prompt
    workflow["7"]["inputs"]["text"] = negative
    workflow["3"]["inputs"]["seed"] = int(seed)
    workflow["3"]["inputs"]["steps"] = int(options.steps)
    workflow["3"]["inputs"]["cfg"] = float(options.cfg)
    workflow["5"]["inputs"]["width"] = width
    workflow["5"]["inputs"]["height"] = height
    client_id = str(uuid.uuid4())
    async with httpx.AsyncClient(timeout=30) as client:
        q = await client.post(f"{settings.comfyui_url.rstrip('/')}/prompt",json={"prompt":workflow,"client_id":client_id})
        q.raise_for_status()
        prompt_id = q.json()["prompt_id"]
    async with httpx.AsyncClient(timeout=30) as client:
        for _ in range(360):
            await asyncio.sleep(1)
            r = await client.get(f"{settings.comfyui_url.rstrip('/')}/history/{prompt_id}")
            r.raise_for_status()
            hist = r.json()
            if prompt_id in hist:
                for node in hist[prompt_id].get("outputs", {}).values():
                    for image in node.get("images", []):
                        params = {"filename":image["filename"],"subfolder":image.get("subfolder",""),"type":image.get("type","output")}
                        ir = await client.get(f"{settings.comfyui_url.rstrip('/')}/view",params=params)
                        ir.raise_for_status()
                        out_path.parent.mkdir(parents=True,exist_ok=True)
                        out_path.write_bytes(ir.content)
                        return
                raise RuntimeError("ComfyUI finished without an image")
    raise TimeoutError("ComfyUI generation timed out")

def make_timeline(storyboard: AudioStoryboard):
    return [{"start":s.start_seconds,"end":s.end_seconds,"image":f"scenes/scene_{s.scene_number:03d}/image_001.png"} for s in storyboard.scenes]

def zip_project(project_dir: Path) -> Path:
    exports = project_dir / "exports"
    exports.mkdir(exist_ok=True)
    target = exports / "storyboard_export.zip"
    with zipfile.ZipFile(target,"w",zipfile.ZIP_DEFLATED) as z:
        for p in project_dir.rglob("*"):
            if p.is_file() and p != target: z.write(p,p.relative_to(project_dir))
    return target
