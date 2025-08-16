# Amrisha

## Blender video generation

    A ready-to-run Blender Python script that builds a complete, detailed, ~40-second cinematic showing your device concept with only Blender primitives (no logo, no external assets):
        Arm (cylinder) with a skin shader
        Wearable band (torus) + device body (cube)
        Snake (curve + bevel) that slithers in and bites
        Venom spread: animated red “vein” mask expanding from bite
        Antidote release: blue emission pulses from device location and overrides red
        Simple holo UI (“Antidote Engaged”) that appears during release
        Keyframed camera moves, dramatic lighting
        Eevee 1080p @ 30 fps, MP4 (H.264 + AAC)

## How to use

    Workflow
        Run Python outside Blender first to generate narration:
            pip install gTTS
            python narrate.py
        → Produces amrisha.wav
        Place amrisha.wav + music.mp3 in the same directory as Blender file.

        Open Blender → Scripting → New Script → Paste my full script → Run.
        Scene auto-builds (arm, device, snake, venom spread, antidote).
        Audio strips are added automatically.
        Camera animates.

        Render produces amrisha.mp4.
            Open Blender → Scripting → New → paste this → Run.
            Then File → Defaults are set; to render: Render → Render Animation (or press Ctrl+F12).

## What you’ll see

    0–6s: Camera reveals wearable on arm; atmosphere is dark, moody.
    6–7s: Snake “appears” and reaches the wrist path.
    7s (Frame ~210): Quick strike — screen flashes red.
    7–17s: Venom red mask expands outward from bite point on the arm surface.
    17–27s: Antidote blue glow propagates from device to the bite area, overriding red.
    27–40s: Everything cools down; device returns to calm cyan; snake retreats; camera eases out.

    Render
        Open Blender → Scripting → paste script → Run.
        Then Render → Render Animation (or Ctrl+F12).
        The MP4 will be written to your project folder as amrisha.mp4