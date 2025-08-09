"""
Amrisha Demo
-------------------------
A simple, editable 3D simulation demonstrating the use-case:
 - snake approaches and bites an arm
 - venom particles travel into the arm
 - wearable detects venom, classifies, and triggers auto-injector
 - antidote injection and recovery animation

Run with: python demo.py
Dependencies: vpython
Install: pip install vpython
"""

from vpython import *
from random import random
import time
import math

# ----------------------
# Configurable parameters
# ----------------------
CFG = {
    "approach_time": 2.0,        # seconds for snake to approach
    "bite_time": 0.6,            # seconds snake spends biting
    "venom_emit_count": 40,      # number of particles emitted during bite
    "detection_delay": 1.2,      # time after venom enters until detection
    "classification_time": 0.8,  # AI classification time
    "injection_time": 0.8,       # time for needle to inject
    "recovery_time": 3.0,        # recovery duration
    "particle_speed": 1.2,
    "particle_lifetime": 3.5,
    "scene_scale": 1.0,
    "window_width": 1000,
    "window_height": 600
}

# ----------------------
# Helper utilities
# ----------------------
def ease_in_out(t):
    return (1 - math.cos(math.pi * t)) / 2

# ----------------------
# Build scene
# ----------------------
scene.title = "Amrisha Demo"
scene.width = CFG["window_width"]
scene.height = CFG["window_height"]
scene.background = color.gray(0.07)
scene.forward = vector(-0.3, -0.2, -1)

# Ground/plane for reference
ground = box(pos=vector(0, -0.9, 0), size=vector(10, 0.1, 6), color=color.gray(0.1), opacity=0.8)

# Arm (rounded cylinder approximation using a long cylinder)
arm = cylinder(pos=vector(-0.5, -0.6, 0), axis=vector(3.2, 0.0, 0), radius=0.28, color=vector(1.0,0.86,0.72))
# Slight rotation to appear natural
arm.rotate(angle=0.14, axis=vector(0,0,1), origin=arm.pos)

# Wrist area marker
wrist_center = vector(1.1, -0.55, 0)

# Watch / wearable
watch_body = box(pos=wrist_center + vector(0.18, 0.12, 0), size=vector(0.7, 0.3, 0.28), color=color.darkgray)
watch_screen = box(pos=wrist_center + vector(0.18, 0.12, 0.15), size=vector(0.58, 0.22, 0.02), color=color.black, emissive=True)

# Antidote cartridge (inside housing visually) — axis used to represent remaining "length"
cartridge = cylinder(pos=wrist_center + vector(0.4, 0.0, 0), axis=vector(0.6, 0, 0), radius=0.08, color=color.cyan, opacity=0.9)

# Needle (initially retracted)
needle = cylinder(pos=wrist_center + vector(0.85, -0.05, 0), axis=vector(0.0, 0.0, 0.0), radius=0.02, color=color.white, opacity=0.95)
needle.visible = False

# Simple 'AI chip' block on housing (visual)
chip = box(pos=wrist_center + vector(0.0, 0.18, 0.12), size=vector(0.12,0.08,0.04), color=color.blue)

# Display text (using label)
screen_label = label(pos=watch_screen.pos + vector(0,0,0.06), text='IDLE', xoffset=0, yoffset=0,
                     box=False, height=18, color=color.white, opacity=0, line=False, font='sans')

# Simple vitals display (heart rate bar)
hr_bar_bg = box(pos=vector(-3.6,0.9,0), size=vector(1.8,0.18,0.05), color=color.gray(0.15))
hr_bar = box(pos=vector(-3.6,0.9,0), size=vector(0.02,0.14,0.04), color=color.red)
hr_label = label(pos=vector(-3.6,0.98,0), text='Heart rate: -- bpm', box=False, height=12, color=color.white, opacity=0)

# ----------------------
# Snake model (simple chained spheres)
# ----------------------
snake_segments = []
nseg = 10
for i in range(nseg):
    radius = 0.12 - 0.003 * i
    s = sphere(pos=vector(-6.0 + i*0.22, -0.55 + math.sin(i)*0.03, 0.02), radius=radius, color=vector(0.36,0.22,0.12))
    snake_segments.append(s)
snake_head = snake_segments[0]

# ----------------------
# Venom particles pool
# ----------------------
particles = []
for i in range(200):
    p = sphere(pos=vector(100,100,100), radius=0.03, color=color.red, make_trail=False, opacity=0.95)
    p.life = 0.0
    p.v = vector(0,0,0)
    p.active = False
    particles.append(p)

def emit_venom(origin, direction, count):
    emitted = 0
    for p in particles:
        if not p.active:
            p.pos = origin + vector((random()-0.5)*0.04, (random()-0.5)*0.04, (random()-0.5)*0.04)
            jitter_dir = direction + vector((random()-0.5)*0.2, (random()-0.5)*0.2, (random()-0.5)*0.2)
            p.v = norm(jitter_dir) * CFG["particle_speed"] * (0.8 + 0.6*random())
            p.life = CFG["particle_lifetime"] * (0.6 + 0.8*random())
            p.active = True
            p.opacity = 0.95
            emitted += 1
            if emitted >= count:
                break

# ----------------------
# State machine
# ----------------------
state = "idle"
t0 = 0.0
clock = 0.0

# helper to update heart rate visualization (simple proxy)
def set_heart_rate(bpm):
    # map typical bpm 40-160 to bar length 0.02 to 0.9
    val = max(0.02, min(0.9, (bpm-40)/(160-40) * 0.9))
    hr_bar.size.x = val
    hr_bar.pos.x = -3.6 - (0.9 - val)/2.0
    hr_label.text = f'Heart rate: {int(bpm)} bpm'

set_heart_rate(75)

# ----------------------
# Main simulation routine (non-blocking loop)
# ----------------------
def run_simulation():
    global state, t0, clock, needle
    state = "approach"
    t0 = 0.0
    clock = 0.0
    bite_pos = wrist_center + vector(0.2, 0.05, 0.06)
    detection_time_marker = None
    classification = None

    while True:
        rate(50) # 50 frames per second
        dt_local = 1.0 / 50.0   # fixed timestep for predictability
        t0 += dt_local

        # Animate snake approach
        if state == "approach":
            progress = min(1.0, t0 / CFG["approach_time"])
            x = -6.0 + (5.9 * ease_in_out(progress))
            for i, seg in enumerate(snake_segments):
                seg.pos.x = x + i*0.22
            snake_head.pos = snake_segments[0].pos
            if progress >= 1.0:
                state = "bite"
                t0 = 0.0
                screen_label.text = "Bite!"
                screen_label.color = color.yellow

        # Bite state: spawn venom particles for the bite duration
        elif state == "bite":
            if t0 < CFG["bite_time"]:
                # emit particles towards the arm (direction vector)
                dir_vec = norm(arm.pos - bite_pos)
                emit_venom(bite_pos, dir_vec, max(1, int(CFG["venom_emit_count"] * dt_local * 8)))
                screen_label.text = "Venom injected"
                screen_label.color = color.orange
            else:
                state = "venom_spread"
                t0 = 0.0
                detection_time_marker = time.time() + CFG["detection_delay"]
                screen_label.text = "Analyzing..."
                screen_label.color = color.cyan

        # Venom spread: particles move into arm; wait for detection delay
        elif state == "venom_spread":
            if time.time() >= detection_time_marker:
                state = "classify"
                t0 = 0.0
                screen_label.text = "Classifying"
                screen_label.color = color.magenta

        # Classification (AI)
        elif state == "classify":
            if t0 > CFG["classification_time"]:
                classification = "neurotoxic"  # for demo; could be random or parameterized
                state = "inject"
                t0 = 0.0
                screen_label.text = "Venom detected: " + classification
                screen_label.color = color.red
                needle.visible = True
            else:
                # visual pulse on screen during classification
                pass

        # Injection animation
        elif state == "inject":
            # animate the needle moving into arm and cartridge shrinking
            progress = min(1.0, t0 / CFG["injection_time"])
            needle.axis = vector(-0.22*progress, 0, 0)
            needle.pos = wrist_center + vector(0.85 - 0.22*progress, -0.05, 0)
            # adjust cartridge axis to simulate depletion
            remaining = max(0.05, 0.6*(1.0-progress))
            cartridge.axis = vector(remaining, 0, 0)
            if progress >= 1.0:
                state = "recover"
                t0 = 0.0
                screen_label.text = "Antidote delivered"
                screen_label.color = color.green

        # Recovery
        elif state == "recover":
            # fade particles and slowly return heart rate to baseline
            progress = min(1.0, t0 / CFG["recovery_time"])
            # drain active particles faster
            for p in particles:
                if p.active:
                    p.life -= dt_local * 1.4
                    if p.life <= 0:
                        p.active = False
                        p.pos = vector(100,100,100)
            # heart rate returns to baseline 75
            current_hr = 75 + (1.0-progress) * 20  # demo bounce back
            set_heart_rate(current_hr)
            if progress >= 1.0:
                screen_label.text = "Stable"
                screen_label.color = color.white
                needle.visible = False
                break

        # Update particle motion every loop
        for p in particles:
            if p.active:
                p.pos += p.v * dt_local
                # simple dispersion
                p.v = p.v * (1.0 - 0.05*dt_local)
                p.life -= dt_local
                p.opacity = max(0.0, p.life / CFG["particle_lifetime"])
                if p.life <= 0:
                    p.active = False
                    p.pos = vector(100,100,100)

    # end simulation
    return

# ----------------------
# Run if executed directly
# ----------------------
print("Amrisha demo saved. To run the simulation call run_simulation() or run this file directly.")
if __name__ == '__main__':
    run_simulation()
