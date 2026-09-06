from __future__ import annotations
import asyncio
import json
import shutil
import uuid
from typing import Any

import httpx
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from .adapters import sonic_diffusion, sound2scene
from .config import settings
from .models import AudioStoryboard, GenerationOptions, ProjectStatus
from .services import comfy_generate, extract_scene_audio, make_timeline, plan_storyboard, probe_duration, safe_project_id, transcribe, zip_project

app = FastAPI(title="MoneyPrint Junior Audio-to-Image", version="0.1.0")
app.add_middleware(CORSMiddleware,allow_origins=["http://localhost:5173","http://127.0.0.1:5173"],allow_credentials=True,allow_methods=["*"],allow_headers=["*"])

STATUS: dict[str, ProjectStatus] = {}
CANCEL: dict[str, asyncio.Event] = {}

def set_status(pid: str, stage: str, detail: str = "", progress: float = 0):
    STATUS[pid] = ProjectStatus(project_id=pid,stage=stage,detail=detail,progress=progress,cancelled=CANCEL.get(pid,asyncio.Event()).is_set())

@app.get("/api/health")
async def health():
    checks: dict[str,Any] = {"ffmpeg":shutil.which("ffmpeg") is not None,"ffprobe":shutil.which("ffprobe") is not None,"ollama":False,"comfyui":False,"sonicdiffusion":sonic_diffusion.status(),"sound2scene":sound2scene.status(),"whisper_backend":{"requested_device":settings.whisper_device,"note":"auto uses CPU/int8 on generic Windows; no fake DirectML claim"},"image_backend":"ComfyUI HTTP API"}
    async with httpx.AsyncClient(timeout=2) as client:
        try: checks["ollama"] = (await client.get(f"{settings.ollama_url.rstrip('/')}/api/tags")).is_success
        except Exception: pass
        try: checks["comfyui"] = (await client.get(f"{settings.comfyui_url.rstrip('/')}/system_stats")).is_success
        except Exception: pass
    return checks

@app.post("/api/projects")
async def create_project(audio: UploadFile=File(...), options_json: str=Form("{}")):
    suffix = __import__("pathlib").Path(audio.filename or "").suffix.lower()
    if suffix not in {".wav",".mp3",".m4a"}: raise HTTPException(400,"Only WAV, MP3 and M4A are supported")
    try: options = GenerationOptions.model_validate(json.loads(options_json))
    except Exception as e: raise HTTPException(400,f"Invalid options: {e}")
    pid = str(uuid.uuid4())
    pdir = settings.storage_path / pid
    srcdir = pdir / "source_audio"
    srcdir.mkdir(parents=True)
    source = srcdir / f"source{suffix}"
    with source.open("wb") as f:
        while chunk := await audio.read(1024*1024): f.write(chunk)
    CANCEL[pid] = asyncio.Event()
    set_status(pid,"Queued","Project created",0)
    asyncio.create_task(run_pipeline(pid,source,pdir,options))
    return {"project_id":pid}

async def run_pipeline(pid, source, pdir, options):
    try:
        ev = CANCEL[pid]
        set_status(pid,"Reading audio","Running FFprobe",0.03)
        duration = await asyncio.to_thread(probe_duration,source)
        if ev.is_set(): return
        set_status(pid,"Transcribing",f"Using faster-whisper {settings.whisper_model}",0.12)
        transcript = await asyncio.to_thread(transcribe,source)
        (pdir/"transcript.json").write_text(json.dumps(transcript,indent=2,ensure_ascii=False),encoding="utf-8")
        if ev.is_set(): return
        set_status(pid,"Understanding story",f"Ollama {settings.ollama_model}",0.28)
        storyboard = await plan_storyboard(transcript,duration,options)
        (pdir/"storyboard.json").write_text(storyboard.model_dump_json(indent=2),encoding="utf-8")
        (pdir/"timeline.json").write_text(json.dumps(make_timeline(storyboard),indent=2),encoding="utf-8")
        if ev.is_set(): return
        total = sum(s.image_count for s in storyboard.scenes)
        done = 0
        for scene in storyboard.scenes:
            if ev.is_set(): return
            sdir = pdir/"scenes"/f"scene_{scene.scene_number:03d}"
            sdir.mkdir(parents=True,exist_ok=True)
            await asyncio.to_thread(extract_scene_audio,source,sdir/"audio.wav",scene.start_seconds,scene.end_seconds)
            (sdir/"prompt.json").write_text(scene.model_dump_json(indent=2),encoding="utf-8")
            for index in range(scene.image_count):
                if ev.is_set(): return
                done += 1
                set_status(pid,f"Generating scene {scene.scene_number}",f"Image {index+1}/{scene.image_count}",0.35+0.6*(done/max(total,1)))
                if options.image_engine != "comfyui":
                    msg = sonic_diffusion.status()["message"] if options.image_engine=="sonicdiffusion" else sound2scene.status()["message"]
                    raise RuntimeError(msg)
                out = sdir/f"image_{index+1:03d}.png"
                await comfy_generate(scene.image_prompt,scene.negative_prompt,options,out,options.seed+scene.scene_number*1000+index)
        set_status(pid,"Finalizing storyboard","Writing export package",0.97)
        await asyncio.to_thread(zip_project,pdir)
        set_status(pid,"Complete","Storyboard and images are ready",1)
    except Exception as e:
        if CANCEL.get(pid) and CANCEL[pid].is_set(): set_status(pid,"Cancelled","Generation stopped safely",STATUS.get(pid,ProjectStatus(project_id=pid,stage="Cancelled")).progress)
        else: set_status(pid,"Error",str(e),STATUS.get(pid,ProjectStatus(project_id=pid,stage="Error")).progress)

@app.get("/api/projects/{project_id}/status")
async def project_status(project_id: str):
    try: pid = safe_project_id(project_id)
    except ValueError: raise HTTPException(400,"Invalid project id")
    if pid not in STATUS: raise HTTPException(404,"Project not found")
    return STATUS[pid]

@app.get("/api/projects/{project_id}/storyboard")
async def get_storyboard(project_id: str):
    try: pid = safe_project_id(project_id)
    except ValueError: raise HTTPException(400,"Invalid project id")
    path = settings.storage_path/pid/"storyboard.json"
    if not path.exists(): raise HTTPException(404,"Storyboard not ready")
    return json.loads(path.read_text(encoding="utf-8"))

@app.post("/api/projects/{project_id}/cancel")
async def cancel_project(project_id: str):
    try: pid = safe_project_id(project_id)
    except ValueError: raise HTTPException(400,"Invalid project id")
    if pid not in CANCEL: raise HTTPException(404,"Project not found")
    CANCEL[pid].set()
    set_status(pid,"Cancelling","Stop requested; saved scenes remain intact",STATUS.get(pid,ProjectStatus(project_id=pid,stage="Cancelling")).progress)
    return {"ok":True}

@app.post("/api/projects/{project_id}/scenes/{scene_number}/regenerate")
async def regenerate_scene(project_id: str, scene_number: int, body: dict[str,Any]):
    try: pid = safe_project_id(project_id)
    except ValueError: raise HTTPException(400,"Invalid project id")
    pdir = settings.storage_path/pid
    sb_path = pdir/"storyboard.json"
    if not sb_path.exists(): raise HTTPException(404,"Storyboard not found")
    sb = AudioStoryboard.model_validate_json(sb_path.read_text(encoding="utf-8"))
    scene = next((s for s in sb.scenes if s.scene_number==scene_number),None)
    if not scene: raise HTTPException(404,"Scene not found")
    if "image_prompt" in body: scene.image_prompt = str(body["image_prompt"])
    if "negative_prompt" in body: scene.negative_prompt = str(body["negative_prompt"])
    opts = GenerationOptions.model_validate(body.get("options",{}))
    seed = int(body.get("seed",opts.seed+scene_number*1000))
    out = pdir/"scenes"/f"scene_{scene_number:03d}"/"image_001.png"
    await comfy_generate(scene.image_prompt,scene.negative_prompt,opts,out,seed)
    sb_path.write_text(sb.model_dump_json(indent=2),encoding="utf-8")
    return {"ok":True}

@app.get("/api/projects/{project_id}/images/{scene_number}/{image_number}")
async def get_image(project_id: str, scene_number: int, image_number: int):
    try: pid = safe_project_id(project_id)
    except ValueError: raise HTTPException(400,"Invalid project id")
    p = settings.storage_path/pid/"scenes"/f"scene_{scene_number:03d}"/f"image_{image_number:03d}.png"
    if not p.exists(): raise HTTPException(404,"Image not found")
    return FileResponse(p)

@app.get("/api/projects/{project_id}/export")
async def export_project(project_id: str):
    try: pid = safe_project_id(project_id)
    except ValueError: raise HTTPException(400,"Invalid project id")
    pdir = settings.storage_path/pid
    if not pdir.exists(): raise HTTPException(404,"Project not found")
    target = await asyncio.to_thread(zip_project,pdir)
    return FileResponse(target,filename=f"{pid}-storyboard.zip")
