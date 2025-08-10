import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import imageio
import os

# ==============================
# Parameters
# ==============================
fps = 20
seconds_per_scene = 3
output_file = "amrisha_story.mp4"
frames_dir = "frames"
os.makedirs(frames_dir, exist_ok=True)

# Arm model parameters
arm_length = 8
arm_radius = 1
device_length = 1
device_radius = 0.6

# Colors
skin_color = (1.0, 0.8, 0.6)
venom_color = (0.8, 0.0, 0.0)
antidote_color = (0.0, 0.5, 1.0)
device_idle = (0.2, 0.2, 0.2)
device_active = (0.0, 1.0, 0.0)

# ==============================
# Utility: Create Cylinder
# ==============================
def create_cylinder(radius, height, z_offset=0, color=(1,0,0)):
    theta = np.linspace(0, 2*np.pi, 30)
    z = np.linspace(0, height, 2)
    theta, z = np.meshgrid(theta, z)
    x = radius * np.cos(theta)
    y = radius * np.sin(theta)
    z = z + z_offset
    return x, y, z

# ==============================
# Render Scene
# ==============================
def render_scene(ax, venom_progress=0.0, antidote_progress=0.0, device_on=False, snake_near=False):
    # Draw arm
    X, Y, Z = create_cylinder(arm_radius, arm_length)
    ax.plot_surface(X, Y, Z, color=skin_color, alpha=1.0, shade=True)

    # Draw device
    Xd, Yd, Zd = create_cylinder(device_radius, device_length, z_offset=arm_length/2 - device_length/2)
    dev_color = device_active if device_on else device_idle
    ax.plot_surface(Xd, Yd, Zd, color=dev_color, alpha=1.0, shade=True)

    # Draw venom spread
    if venom_progress > 0:
        venom_height = venom_progress * arm_length
        Xv, Yv, Zv = create_cylinder(arm_radius*0.95, venom_height)
        ax.plot_surface(Xv, Yv, Zv, color=venom_color, alpha=0.6, shade=True)

    # Draw antidote spread
    if antidote_progress > 0:
        anti_height = antidote_progress * arm_length
        Xa, Ya, Za = create_cylinder(arm_radius*0.9, anti_height)
        ax.plot_surface(Xa, Ya, Za, color=antidote_color, alpha=0.6, shade=True)

    # Draw snake head (optional)
    if snake_near:
        u = np.linspace(0, np.pi, 20)
        v = np.linspace(0, 2*np.pi, 20)
        r = 1.0
        xs = r * np.outer(np.sin(u), np.cos(v)) + 0
        ys = r * np.outer(np.sin(u), np.sin(v)) + 3
        zs = r * np.outer(np.cos(u), np.ones_like(v)) + 0
        ax.plot_surface(xs, ys, zs, color=(0.1, 0.6, 0.1), alpha=1.0, shade=True)

    ax.set_xlim(-3, 3)
    ax.set_ylim(-3, 5)
    ax.set_zlim(0, arm_length)
    ax.view_init(elev=20, azim=60)
    ax.axis("off")

# ==============================
# Generate Frames
# ==============================
frame_count = 0
frames = []

# Scene 1: Arm idle
for _ in range(seconds_per_scene * fps):
    fig = plt.figure(figsize=(6,6))
    ax = fig.add_subplot(111, projection='3d')
    render_scene(ax)
    fname = f"{frames_dir}/frame_{frame_count:04d}.png"
    plt.savefig(fname, dpi=150)
    frames.append(imageio.imread(fname))
    plt.close(fig)
    frame_count += 1

# Scene 2: Snake approaches
for i in range(seconds_per_scene * fps):
    fig = plt.figure(figsize=(6,6))
    ax = fig.add_subplot(111, projection='3d')
    render_scene(ax, snake_near=(i > fps))
    fname = f"{frames_dir}/frame_{frame_count:04d}.png"
    plt.savefig(fname, dpi=150)
    frames.append(imageio.imread(fname))
    plt.close(fig)
    frame_count += 1

# Scene 3: Venom spreading
for i in range(seconds_per_scene * fps):
    fig = plt.figure(figsize=(6,6))
    ax = fig.add_subplot(111, projection='3d')
    render_scene(ax, venom_progress=i / (seconds_per_scene * fps), snake_near=True)
    fname = f"{frames_dir}/frame_{frame_count:04d}.png"
    plt.savefig(fname, dpi=150)
    frames.append(imageio.imread(fname))
    plt.close(fig)
    frame_count += 1

# Scene 4: Device activates + Antidote spreading
for i in range(seconds_per_scene * fps):
    fig = plt.figure(figsize=(6,6))
    ax = fig.add_subplot(111, projection='3d')
    render_scene(ax, venom_progress=1.0, antidote_progress=i / (seconds_per_scene * fps), device_on=True)
    fname = f"{frames_dir}/frame_{frame_count:04d}.png"
    plt.savefig(fname, dpi=150)
    frames.append(imageio.imread(fname))
    plt.close(fig)
    frame_count += 1

# Scene 5: Fully recovered
for _ in range(seconds_per_scene * fps):
    fig = plt.figure(figsize=(6,6))
    ax = fig.add_subplot(111, projection='3d')
    render_scene(ax, antidote_progress=1.0, device_on=True)
    fname = f"{frames_dir}/frame_{frame_count:04d}.png"
    plt.savefig(fname, dpi=150)
    frames.append(imageio.imread(fname))
    plt.close(fig)
    frame_count += 1

# ==============================
# Save MP4
# ==============================
imageio.mimsave(output_file, frames, fps=fps)
print(f"✅ MP4 saved as {output_file}")
