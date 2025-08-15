#!/usr/bin/env python3
"""
QuantumVenom realistic image-based pitch video generator
- Uses hardcoded royalty-free image/audio URLs (replace if needed)
- Produces a cinematic 1080p MP4 with captions and animated overlays

Run:
  pip install moviepy pillow opencv-python numpy requests
  python quantumvenom_realistic_pitch.py

Output:
  quantumvenom_pitch_realistic.mp4
"""

import os
import math
import io
import sys
import time
import requests
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from moviepy.editor import ImageSequenceClip, AudioFileClip, concatenate_videoclips, CompositeVideoClip

def ease_in_out(t):
    """Easing function for smooth animations (0 <= t <= 1)."""
    return 0.5 * (1 - math.cos(math.pi * t))

# ---------------------------
# CONFIG - replace URLs if you want different images/music
# ---------------------------
OUTFILE = "quantumvenom_pitch_realistic.mp4"
W, H = 1920, 1080
FPS = 30

# durations (seconds)
SCENE_IDLE = 2.0
SCENE_THREAT = 2.5
SCENE_VENOM = 3.0
SCENE_ANTIDOTE = 3.0
SCENE_RECOVER = 2.0

# Hardcoded royalty-free assets (these are example Unsplash/Pexels links — replace if necessary)
# IMPORTANT: If any link fails, replace with your own direct image URL or local path.
IMG_WRIST = "https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?auto=format&fit=crop&w=1600&q=80"  # wrist/watch
IMG_WRIST_ALT = "https://images.unsplash.com/photo-1523475472560-d2df97ec485c?auto=format&fit=crop&w=1600&q=80"  # alternate wrist
IMG_SNAKE = "https://images.unsplash.com/photo-1517841905240-472988babdf9?auto=format&fit=crop&w=1600&q=80"  # snake (example)
# A dramatic cinematic audio (royalty-free example). Replace if this link is inaccessible.
AUDIO_URL = "https://cdn.pixabay.com/download/audio/2022/03/15/audio_0e80d8e2b1.mp3?filename=dramatic-ambience-117417.mp3"

# Captions per scene
CAPTIONS = [
    ("Wearable Ready", SCENE_IDLE),
    ("Threat Detected", SCENE_THREAT),
    ("Venom Spreading", SCENE_VENOM),
    ("Antidote Released", SCENE_ANTIDOTE),
    ("Patient Stable", SCENE_RECOVER),
]

# Bite point relative position on wrist image (x fraction, y fraction)
# If you replace wrist images, you may need to adjust this.
BITE_POINT = (0.58, 0.48)

# Font (Pillow). Try to load a system font; fallback to default.
def load_font(size=42):
    try:
        # try common fonts
        return ImageFont.truetype("DejaVuSans-Bold.ttf", size)
    except Exception:
        try:
            return ImageFont.truetype("arial.ttf", size)
        except Exception:
            return ImageFont.load_default()

# ---------------------------
# Utility: download remote resource
# ---------------------------
def download_to_image(url):
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    return Image.open(io.BytesIO(resp.content)).convert("RGBA")

def download_to_file(url, dest):
    resp = requests.get(url, stream=True, timeout=60)
    resp.raise_for_status()
    with open(dest, "wb") as f:
        for chunk in resp.iter_content(8192):
            f.write(chunk)
    return dest

# ---------------------------
# Visual helpers
# ---------------------------
def resize_and_letterbox(img: Image.Image, target_w: int, target_h: int):
    img_w, img_h = img.size
    # compute scale preserving aspect
    scale = min(target_w / img_w, target_h / img_h)
    new_w, new_h = int(img_w * scale), int(img_h * scale)
    img_rs = img.resize((new_w, new_h), Image.LANCZOS)
    # paste onto white background centered
    background = Image.new("RGBA", (target_w, target_h), (255, 255, 255, 255))
    x = (target_w - new_w) // 2
    y = (target_h - new_h) // 2
    background.paste(img_rs, (x, y), img_rs)
    return background, (x, y, new_w, new_h)

def radial_glow_mask(size, center, radius, color=(255, 0, 0), strength=1.0):
    """Create an RGBA image with a colored radial glow centered at center with given radius (pixels)."""
    W, H = size
    mask = Image.new("RGBA", (W, H), (0,0,0,0))
    draw = ImageDraw.Draw(mask)
    # build radial gradient by drawing concentric circles with decreasing alpha
    max_r = radius
    for r in range(max_r, 0, -4):
        a = int(200 * (r / max_r) * strength)
        col = (color[0], color[1], color[2], max(0, min(255, a)))
        # ellipse bounding box
        bbox = [center[0]-r, center[1]-r, center[0]+r, center[1]+r]
        draw.ellipse(bbox, fill=col)
    # blur for softness
    mask = mask.filter(ImageFilter.GaussianBlur(radius=max(8, radius//8)))
    return mask

def blend_overlay(base: Image.Image, overlay: Image.Image, alpha=1.0):
    return Image.alpha_composite(base.convert("RGBA"), overlay.convert("RGBA"))

# ---------------------------
# Frame generation for each scene
# ---------------------------
def make_scene_frames(bg_img: Image.Image, overlay_img: Image.Image, caption: str,
                      duration: float, fps: int, scene_type: str,
                      bite_rel=BITE_POINT):
    """
    scene_type: 'idle', 'threat', 'venom', 'antidote', 'recover'
    bg_img: background wrist/snake image (RGBA)
    overlay_img: alternate image used for threat or device shot (RGBA)
    """
    frames = []
    nframes = int(duration * fps)
    font_title = load_font(56)
    font_small = load_font(32)

    # For convenience, pre-resize backgrounds to W,H and get placement box
    bg_main, box_main = resize_and_letterbox(bg_img, W, H)
    if overlay_img is not None:
        bg_overlay, box_overlay = resize_and_letterbox(overlay_img, W, H)
    else:
        bg_overlay, box_overlay = None, None

    for i in range(nframes):
        t = i / max(1, nframes - 1)  # 0..1

        # Start with base background
        if scene_type == "threat":
            # crossfade from wrist to snake overlay: progress only in 'threat'
            cross = ease_in_out(t)
            base = Image.blend(bg_main, bg_overlay, cross if bg_overlay else 0.0)
        elif scene_type in ("venom", "antidote"):
            # keep the snake background for venom scenes if provided
            base = bg_overlay if bg_overlay else bg_main
        elif scene_type == "recover":
            base = bg_main
        else:
            base = bg_main

        frame = base.copy().convert("RGBA")

        # compute bite center in pixel coordinates (map relative bite_rel from base image placement)
        # bite_rel is in 0..1 relative to the inner resized image
        # map to placed box_main coordinate space
        bx_rel, by_rel = bite_rel
        # if using overlay image for venom, use box_overlay as reference (when scene uses overlay)
        ref_box = box_overlay if (scene_type in ("threat","venom") and bg_overlay is not None) else box_main
        x0, y0, w0, h0 = ref_box
        bite_x = int(x0 + bx_rel * w0)
        bite_y = int(y0 + by_rel * h0)

        # Prepare overlay based on scene type
        if scene_type == "venom":
            # radius grows from small to large
            radius = int(20 + ease_in_out(t) * max(W, H) * 0.45)
            glow = radial_glow_mask((W, H), (bite_x, bite_y), radius, color=(220, 40, 40), strength=1.0)
            frame = Image.alpha_composite(frame, glow)
            # add a pulsating light on the device (small)
            # small red tint near device location (approx near right-middle)
        elif scene_type == "antidote":
            # blue antidote spreads from device location (we'll choose device placed at wrist center)
            # antidote radius grows but reverse-looking: starts near device and floods downward/upward
            radius = int(20 + ease_in_out(t) * max(W, H) * 0.5)
            # device center approximated near bite (or slightly offset) - we'll take near bite for demo
            glow = radial_glow_mask((W, H), (bite_x, bite_y), radius, color=(40, 160, 255), strength=1.0)
            # composite but with less opacity
            frame = Image.alpha_composite(frame, glow)
        elif scene_type == "threat":
            # maybe add a subtle vignette or red edge to imply danger ramping up
            vign = radial_glow_mask((W, H), (int(W/2), int(H/2)), int(min(W,H)*0.75), color=(160,30,30), strength=0.12*(t))
            frame = Image.alpha_composite(frame, vign)
        elif scene_type == "idle":
            # slight gentle vignette for polish
            vign = radial_glow_mask((W, H), (int(W/2), int(H/2)), int(min(W,H)*0.9), color=(10,10,10), strength=0.06*(1.0 - t))
            frame = Image.alpha_composite(frame, vign)
        elif scene_type == "recover":
            # gentle green tint to show recovery
            glow = radial_glow_mask((W, H), (bite_x, bite_y), int(min(W,H)*0.35), color=(60,200,120), strength=0.35*(ease_in_out(t)))
            frame = Image.alpha_composite(frame, glow)

        # Add text caption (center or bottom style depending in main)
        draw = ImageDraw.Draw(frame)
        # Title center lower-third
        wtext, htext = draw.textsize(caption_text := caption_str_for_scene(scene_type), font=font_title)
        # center lower third
        caption_x = (W - wtext) // 2
        caption_y = int(H * 0.75)
        # draw a subtle semi-transparent rectangle behind caption
        rect_pad_x = 32
        rect_pad_y = 16
        rect = [caption_x - rect_pad_x, caption_y - rect_pad_y,
                caption_x + wtext + rect_pad_x, caption_y + htext + rect_pad_y]
        draw.rectangle(rect, fill=(0,0,0,120))
        draw.text((caption_x, caption_y), caption_text, font=font_title, fill=(255,255,255,255))

        # small heart-rate / footer
        hr_text = hr_text_for_scene(scene_type, t)
        draw.text((40, H - 80), hr_text, font=font_small, fill=(255,255,255,220))

        # convert to RGB (moviepy works with RGB arrays)
        frame_rgb = frame.convert("RGB")
        frames.append(np.asarray(frame_rgb))

    return frames

# Helper to map scene_type to caption text
def caption_str_for_scene(scene_type):
    return {
        "idle": "QuantumVenom — Ready to Protect",
        "threat": "Venomous Bite Detected",
        "venom": "Venom Spreading — Immediate Response Required",
        "antidote": "Antidote Released — Neutralizing Toxins",
        "recover": "Patient Stable — Monitoring",
    }.get(scene_type, "")

def hr_text_for_scene(scene_type, t):
    if scene_type == "venom":
        bpm = int(75 + 40 * t)
    elif scene_type == "antidote":
        bpm = int(115 - 30 * t)
    else:
        bpm = 76
    return f"Heart rate: {bpm} bpm"

# ---------------------------
# Main assembly
# ---------------------------
def main():
    print("Starting QuantumVenom video build...")
    os.makedirs("tmp_qv", exist_ok=True)

    # Download assets
    print("Downloading images (may take a few seconds)...")
    try:
        wrist_img = download_to_image(IMG_WRIST)
    except Exception as e:
        print("Failed downloading main wrist image:", e)
        sys.exit(1)
    try:
        wrist_alt_img = download_to_image(IMG_WRIST_ALT)
    except Exception:
        wrist_alt_img = wrist_img
    try:
        snake_img = download_to_image(IMG_SNAKE)
    except Exception as e:
        print("Failed downloading snake image:", e)
        snake_img = wrist_alt_img

    # Download audio
    audio_path = None
    try:
        audio_path = os.path.join("tmp_qv", "qv_bed.mp3")
        print("Downloading audio...")
        download_to_file(AUDIO_URL, audio_path)
    except Exception as e:
        print("Audio download failed, proceeding without audio:", e)
        audio_path = None

    # build scenes (frames)
    all_frames = []

    # Scene 1: Idle (wearable)
    print("Rendering Scene: Idle")
    frames = make_scene_frames(bg_img=wrist_img, overlay_img=None, caption="Wearable Ready",
                               duration=SCENE_IDLE, fps=FPS, scene_type="idle")
    all_frames.extend(frames)

    # Scene 2: Threat (snake approach crossfade)
    print("Rendering Scene: Threat")
    frames = make_scene_frames(bg_img=wrist_img, overlay_img=snake_img, caption="Threat Detected",
                               duration=SCENE_THREAT, fps=FPS, scene_type="threat")
    all_frames.extend(frames)

    # Scene 3: Venom spreading
    print("Rendering Scene: Venom")
    frames = make_scene_frames(bg_img=snake_img, overlay_img=snake_img, caption="Venom Spreading",
                               duration=SCENE_VENOM, fps=FPS, scene_type="venom")
    all_frames.extend(frames)

    # Scene 4: Antidote release (back to wrist image with blue overlay)
    print("Rendering Scene: Antidote")
    frames = make_scene_frames(bg_img=wrist_img, overlay_img=wrist_img, caption="Antidote Released",
                               duration=SCENE_ANTIDOTE, fps=FPS, scene_type="antidote")
    all_frames.extend(frames)

    # Scene 5: Recover
    print("Rendering Scene: Recover")
    frames = make_scene_frames(bg_img=wrist_img, overlay_img=None, caption="Patient Stable",
                               duration=SCENE_RECOVER, fps=FPS, scene_type="recover")
    all_frames.extend(frames)

    # Build clip and write video (moviepy)
    print("Building video clip...")
    clip = ImageSequenceClip(all_frames, fps=FPS)

    # Audio
    if audio_path and os.path.exists(audio_path):
        try:
            audio = AudioFileClip(audio_path)
            # trim or loop audio to match duration
            total_dur = clip.duration
            if audio.duration < total_dur:
                # loop
                audio = audio.fx( lambda a: a.set_duration(total_dur) )
            else:
                audio = audio.subclip(0, total_dur)
            clip = clip.set_audio(audio.volumex(0.65))
        except Exception as e:
            print("Warning: could not attach audio:", e)

    # Write final output
    print("Writing final mp4 (this may take a while)...")
    clip.write_videofile(OUTFILE, codec="libx264", audio_codec="aac", bitrate="6000k",
                         threads=0, preset="medium", ffmpeg_params=["-pix_fmt", "yuv420p"])

    print("Done. Output:", OUTFILE)

# ---------------------------
# Reuse helper functions (download wrappers)
# ---------------------------
def download_to_image(url):
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    return Image.open(io.BytesIO(resp.content)).convert("RGBA")

def download_to_file(url, dest):
    resp = requests.get(url, stream=True, timeout=120)
    resp.raise_for_status()
    with open(dest, "wb") as f:
        for chunk in resp.iter_content(8192):
            f.write(chunk)
    return dest

# ---------------------------
if __name__ == "__main__":
    main()