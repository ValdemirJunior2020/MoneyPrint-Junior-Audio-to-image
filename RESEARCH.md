# Research notes

## SonicDiffusion
Upstream: `BurakCanBiner/SonicDiffusion`

Verified:
- Audio-driven image generation/editing with pretrained diffusion models.
- Includes CLAP code plus custom diffusion/attention/UNet code.
- Expects pretrained files under `ckpts`.
- Published requirements pin PyTorch 2.0.1, torchaudio 2.0.2, torchvision 0.15.2 and diffusers 0.27.2.
- The repository does not claim Stable Diffusion 3.

Decision: optional isolated adapter. Do not claim AMD/Windows support until that exact runtime is validated.

## Sound2Scene / Sound2Vision
Upstream: `kaist-ami/Sound2Scene`

Verified:
- Sound2Scene is the CVPR 2023 audio-to-visual latent alignment implementation.
- Sound2Vision is the later extension with environmental-sound and speech examples.
- Sound2Scene docs target Ubuntu 18.04, Python 3.8, CUDA 11.1, PyTorch 1.8.0.
- Sound2Vision docs target Ubuntu 18.04, Python 3.8, CUDA 11.1, PyTorch 1.9.1.
- Sound2Scene uses SWAV, BigGAN and Sound2Scene checkpoints.
- Sound2Vision uses its own environment/face checkpoints.

Decision: optional isolated adapter; do not force old CUDA/PyTorch into the main application.

## Reliable production image path
ComfyUI HTTP API. The app reports whether ComfyUI is actually reachable and does not fake the underlying GPU backend.
