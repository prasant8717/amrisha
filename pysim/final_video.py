# Amrisha – Simple Cinematic Animation + Audio (Blender 3.x+)
# Builds primitives, animates detection → nanodiamonds → quantum sensing → tailored antidote.
# Auto-loads narration.wav + music.mp3 from the .blend folder (if present) and renders MP4.

import bpy, os, math
from mathutils import Vector, Euler

# ========= CONFIG =========
OUTNAME = "amrisha.mp4"
FPS = 30
DURATION_SEC = 42
TOTAL_FRAMES = FPS * DURATION_SEC
RES_X, RES_Y = 1920, 1080

# Audio files to auto-load if present beside the .blend
NARRATION_FILE = "narration.wav"
MUSIC_FILE = "music.mp3"

# Key story beats (frames)
F_THREAT_START   =  60      # snake enters
F_BITE           =  210
F_DETECT_START   =  220     # device detects physiological anomalies
F_ND_INJECT      =  320     # nanodiamonds deploy
F_SENSING_START  =  420     # quantum sensing scan pass
F_ANTIDOTE_START =  520     # tailored antidote delivery
F_RECOVER        =  820
F_END            =  TOTAL_FRAMES

# ========= SCENE SETUP =========
def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_EEVEE'
    sc.frame_start = 1
    sc.frame_end = TOTAL_FRAMES
    sc.render.fps = FPS
    sc.render.resolution_x = RES_X
    sc.render.resolution_y = RES_Y
    sc.render.resolution_percentage = 100

    # Eevee look
    sc.eevee.use_bloom = True
    sc.eevee.bloom_intensity = 0.06
    sc.eevee.use_gtao = True
    sc.eevee.use_ssr = True
    sc.view_settings.look = 'Medium High Contrast'

    # World
    sc.world.use_nodes = True
    wn = sc.world.node_tree
    for n in wn.nodes: wn.nodes.remove(n)
    out = wn.nodes.new("ShaderNodeOutputWorld")
    bg = wn.nodes.new("ShaderNodeBackground")
    bg.inputs[0].default_value = (0.02, 0.02, 0.03, 1.0)
    wn.links.new(bg.outputs['Background'], out.inputs['Surface'])

    # Output
    sc.render.image_settings.file_format = 'FFMPEG'
    sc.render.ffmpeg.format = 'MPEG4'
    sc.render.ffmpeg.codec = 'H264'
    sc.render.ffmpeg.constant_rate_factor = 'HIGH'
    sc.render.ffmpeg.ffmpeg_preset = 'GOOD'
    sc.render.ffmpeg.audio_codec = 'AAC'
    sc.render.ffmpeg.audio_bitrate = 192
    sc.render.filepath = "//" + OUTNAME

# ========= MATERIALS =========
def mat_skin_with_hotspot():
    """Skin with spherical gradient that we animate to show venom hot-spot + antidote fading."""
    m = bpy.data.materials.new("Skin")
    m.use_nodes = True
    nt = m.node_tree
    # Clean
    for n in list(nt.nodes):
        if n.type != 'OUTPUT_MATERIAL':
            nt.nodes.remove(n)
    out = nt.nodes.get("Material Output")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = (0.86, 0.68, 0.56, 1.0)
    bsdf.inputs["Subsurface"].default_value = 0.15
    bsdf.inputs["Roughness"].default_value = 0.6

    tex = nt.nodes.new("ShaderNodeTexCoord")
    mapn = nt.nodes.new("ShaderNodeMapping")
    grad = nt.nodes.new("ShaderNodeTexGradient"); grad.gradient_type = 'SPHERICAL'
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.35
    ramp.color_ramp.elements[1].position = 0.6

    emit_red  = nt.nodes.new("ShaderNodeEmission"); emit_red.inputs['Color'].default_value  = (1.0, 0.08, 0.06, 1); emit_red.inputs['Strength'].default_value = 2.6
    emit_blue = nt.nodes.new("ShaderNodeEmission"); emit_blue.inputs['Color'].default_value = (0.10, 0.55, 1.0, 1); emit_blue.inputs['Strength'].default_value = 3.2

    mix1 = nt.nodes.new("ShaderNodeMixShader")
    mix2 = nt.nodes.new("ShaderNodeMixShader")

    nt.links.new(tex.outputs['Object'], mapn.inputs['Vector'])
    nt.links.new(mapn.outputs['Vector'], grad.inputs['Vector'])
    nt.links.new(grad.outputs['Fac'], ramp.inputs['Fac'])

    nt.links.new(bsdf.outputs['BSDF'], mix1.inputs[1])
    nt.links.new(emit_red.outputs['Emission'], mix1.inputs[2])
    nt.links.new(ramp.outputs['Color'], mix1.inputs['Fac'])

    nt.links.new(mix1.outputs['Shader'], mix2.inputs[1])
    nt.links.new(emit_blue.outputs['Emission'], mix2.inputs[2])
    nt.links.new(ramp.outputs['Color'], mix2.inputs['Fac'])

    nt.links.new(mix2.outputs['Shader'], out.inputs['Surface'])
    return m, mapn

def mat_plastic(color=(0.12,0.12,0.12,1), name="Plastic"):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs['Base Color'].default_value = color
    bsdf.inputs['Roughness'].default_value = 0.25
    bsdf.inputs['Specular'].default_value = 0.5
    return m

def mat_emission(color=(0.1,0.8,1,1), strength=6.0, name="Emit"):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        if n.type != 'OUTPUT_MATERIAL':
            nt.nodes.remove(n)
    out = nt.nodes.get("Material Output")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs['Color'].default_value = color
    em.inputs['Strength'].default_value = strength
    nt.links.new(em.outputs['Emission'], out.inputs['Surface'])
    return m

def mat_glassish(color=(0.3,1.0,0.6,1), name="Glassish", alpha=0.2):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        if n.type != 'OUTPUT_MATERIAL':
            nt.nodes.remove(n)
    out = nt.nodes.get("Material Output")
    mix = nt.nodes.new("ShaderNodeMixShader")
    tr  = nt.nodes.new("ShaderNodeBsdfTransparent")
    pr  = nt.nodes.new("ShaderNodeBsdfPrincipled")
    pr.inputs['Base Color'].default_value = color
    pr.inputs['Transmission'].default_value = 0.7
    pr.inputs['Roughness'].default_value = 0.1
    mix.inputs['Fac'].default_value = alpha
    nt.links.new(tr.outputs['BSDF'], mix.inputs[1])
    nt.links.new(pr.outputs['BSDF'], mix.inputs[2])
    nt.links.new(mix.outputs['Shader'], out.inputs['Surface'])
    m.blend_method = 'BLEND'
    return m

# ========= GEOMETRY =========
def build_geometry():
    # Arm (cylinder)
    bpy.ops.mesh.primitive_cylinder_add(radius=0.12, depth=0.46, location=(0,0,0))
    arm = bpy.context.active_object
    arm.name = "Arm"
    arm.rotation_euler = Euler((math.radians(90), 0, 0))

    # Strap (torus) + Device (cube) + Screen (plane)
    bpy.ops.mesh.primitive_torus_add(major_radius=0.12, minor_radius=0.02, location=(0.0, 0.0, 0.05))
    strap = bpy.context.active_object; strap.name="Strap"; strap.rotation_euler = Euler((math.radians(90),0,0))

    bpy.ops.mesh.primitive_cube_add(size=0.065, location=(0.11, 0.0, 0.05))
    device = bpy.context.active_object; device.name="Amrisha"; device.rotation_euler = Euler((0, math.radians(20), 0))

    bpy.ops.mesh.primitive_plane_add(size=0.046, location=(0.14, 0.0, 0.05))
    screen = bpy.context.active_object; screen.name="Screen"; screen.rotation_euler = Euler((0, math.radians(20), 0))

    # Device port (small circle where nanodiamonds appear)
    bpy.ops.object.empty_add(type='PLAIN_AXES', location=(0.125, 0.0, 0.055))
    port = bpy.context.active_object; port.name = "Inject_Port"

    # Bite target
    bpy.ops.object.empty_add(type='PLAIN_AXES', location=(0.08, 0.0, 0.06))
    bite = bpy.context.active_object; bite.name = "Bite"

    # Snake (curve + bevel)
    bpy.ops.curve.primitive_bezier_curve_add(location=(-0.6,-0.4,0.06))
    snake_path = bpy.context.active_object; snake_path.name="SnakePath"
    pts = snake_path.data.splines[0].bezier_points
    pts[0].co = Vector((-0.6,-0.4,0.06))
    pts[0].handle_left  = pts[0].co + Vector((-0.2,-0.1,0))
    pts[0].handle_right = pts[0].co + Vector((0.2,0.2,0))
    pts[1].co = Vector((0.08,0.0,0.06))
    pts[1].handle_left  = pts[1].co + Vector((-0.2,-0.2,0))
    pts[1].handle_right = pts[1].co + Vector((0.2,0.2,0))
    bpy.ops.curve.primitive_bezier_circle_add(radius=0.015)
    snake_prof = bpy.context.active_object; snake_prof.name = "SnakeProfile"
    snake_path.data.bevel_object = snake_prof
    snake_path.data.resolution_u = 24

    # Venom spheres (few small red emitters inside arm, near bite)
    venom_spheres = []
    for i, off in enumerate([(0.07, 0.00, 0.06), (0.09, 0.02, 0.055), (0.10,-0.02, 0.062)]):
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.008, location=off)
        s = bpy.context.active_object; s.name = f"Venom_{i}"
        venom_spheres.append(s)

    # Nanodiamond spheres (white/blue emitters start at device port)
    nano_spheres = []
    for i, off in enumerate([(0.125, 0.0, 0.055), (0.125, 0.005, 0.055), (0.125, -0.005, 0.055), (0.128, 0.0, 0.053)]):
        bpy.ops.mesh.primitive_ico_sphere_add(radius=0.005, location=off, subdivisions=2)
        n = bpy.context.active_object; n.name = f"Nano_{i}"
        nano_spheres.append(n)

    # Antidote wave (transparent sphere that grows)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.03, location=(0.11,0.0,0.05))
    antidote_wave = bpy.context.active_object; antidote_wave.name = "AntidoteWave"

    return arm, strap, device, screen, port, bite, snake_path, snake_prof, venom_spheres, nano_spheres, antidote_wave

# ========= MATERIAL ASSIGNMENT =========
def assign_materials(arm, strap, device, screen, venom_spheres, nano_spheres, antidote_wave):
    skin_mat, mapping_node = mat_skin_with_hotspot()
    arm.data.materials.append(skin_mat)

    strap.data.materials.append(mat_plastic((0.06,0.06,0.06,1),'Strap'))
    device.data.materials.append(mat_plastic((0.12,0.12,0.12,1),'DeviceBody'))

    screen_mat = mat_emission((0.08,0.8,1,1), strength=4.0, name="ScreenEmit")
    screen.data.materials.append(screen_mat)

    venom_mat = mat_emission((1.0,0.15,0.1,1), strength=8.0, name="VenomEmit")
    for s in venom_spheres:
        s.data.materials.append(venom_mat)

    nano_mat = mat_emission((0.9,0.95,1.0,1), strength=6.5, name="NanoEmit")
    for n in nano_spheres:
        n.data.materials.append(nano_mat)

    antidote_mat = mat_glassish((0.2,1.0,0.7,1), name="AntidoteGlass", alpha=0.6)
    antidote_wave.data.materials.append(antidote_mat)

    return mapping_node, screen_mat

# ========= ANIMATION =========
def animate_snake(snake_path):
    d = snake_path.data
    d.bevel_factor_start = 1.0; d.bevel_factor_end = 1.0
    d.keyframe_insert('bevel_factor_start', frame=1); d.keyframe_insert('bevel_factor_end', frame=1)
    d.bevel_factor_start = 0.0; d.bevel_factor_end = 1.0
    d.keyframe_insert('bevel_factor_start', frame=F_THREAT_START); d.keyframe_insert('bevel_factor_end', frame=F_THREAT_START)
    # Hold near bite then retract
    d.keyframe_insert('bevel_factor_start', frame=F_BITE); d.keyframe_insert('bevel_factor_end', frame=F_BITE)
    d.keyframe_insert('bevel_factor_start', frame=900); d.keyframe_insert('bevel_factor_end', frame=900)
    d.bevel_factor_start = 1.0; d.bevel_factor_end = 1.0
    d.keyframe_insert('bevel_factor_start', frame=1100); d.keyframe_insert('bevel_factor_end', frame=1100)

def animate_screen(screen_mat):
    # Idle: calm cyan; Detection: red flash; Sensing: pulsing cyan; Antidote: bright green/blue; Settle: calm
    em = None
    for n in screen_mat.node_tree.nodes:
        if n.type == 'EMISSION':
            em = n; break
    if not em: return
    def set_em(c, s, f):
        em.inputs['Color'].default_value = c
        em.inputs['Strength'].default_value = s
        em.inputs['Color'].keyframe_insert('default_value', frame=f)
        em.inputs['Strength'].keyframe_insert('default_value', frame=f)

    set_em((0.1,0.8,1.0,1), 3.0, 1)
    set_em((1.0,0.12,0.08,1), 7.0, F_BITE)        # alert on bite
    set_em((0.1,0.8,1.0,1), 4.0, F_DETECT_START) # back to active cyan
    set_em((0.12,0.6,1.0,1), 9.0, F_SENSING_START)
    set_em((0.15,0.9,0.7,1), 9.5, F_ANTIDOTE_START)  # antidote color
    set_em((0.1,0.8,1.0,1), 4.0, F_RECOVER)

def animate_skin_hotspot(mapping_node):
    # Animate spherical gradient scale to imply venom growth then antidote fade
    try:
        mapping_node.inputs['Scale'].default_value = (0.35,0.35,0.35)
        mapping_node.inputs['Scale'].keyframe_insert('default_value', frame=F_BITE)
        mapping_node.inputs['Scale'].default_value = (0.05,0.05,0.05)
        mapping_node.inputs['Scale'].keyframe_insert('default_value', frame=F_SENSING_START)
        mapping_node.inputs['Scale'].default_value = (2.0,2.0,2.0)
        mapping_node.inputs['Scale'].keyframe_insert('default_value', frame=F_RECOVER)
    except Exception as e:
        print("Mapping animation warning:", e)

def animate_nanodiamonds(nano_spheres, port, bite):
    # Four small spheres move from port to bite, staggered
    start = F_ND_INJECT
    travel = 120
    for i, n in enumerate(nano_spheres):
        # start at port
        n.location = port.location.copy()
        n.keyframe_insert('location', frame=start + i*10)
        # mid (inside arm)
        mid = Vector(( (port.location.x + bite.location.x)/2 + 0.02,
                       0.0 + (0.015 if i%2==0 else -0.015),
                       (port.location.z + bite.location.z)/2 ))
        n.location = mid
        n.keyframe_insert('location', frame=start + i*10 + travel//2)
        # end at bite
        n.location = bite.location.copy()
        n.keyframe_insert('location', frame=start + i*10 + travel)
        # gentle fade outward after sensing
        n.location = bite.location + Vector((0.02*(1 if i%2 else -1), 0.0, 0.0))
        n.keyframe_insert('location', frame=F_SENSING_START + 80)

def animate_antidote_wave(antidote_wave):
    # Start small at device, grow through arm with transparency
    antidote_wave.scale = Vector((0.01,0.01,0.01))
    antidote_wave.keyframe_insert('scale', frame=F_ANTIDOTE_START)
    antidote_wave.scale = Vector((2.2,2.2,2.2))
    antidote_wave.keyframe_insert('scale', frame=F_RECOVER)
    # Slight shrink to settle
    antidote_wave.scale = Vector((1.8,1.8,1.8))
    antidote_wave.keyframe_insert('scale', frame=F_END)

def animate_arm_subtle(arm):
    arm.rotation_euler = Euler((math.radians(90), 0, math.radians(-2)))
    arm.keyframe_insert('rotation_euler', frame=1)
    arm.rotation_euler = Euler((math.radians(90), 0, math.radians(2)))
    arm.keyframe_insert('rotation_euler', frame=(F_RECOVER//2))
    arm.rotation_euler = Euler((math.radians(90), 0, math.radians(-2)))
    arm.keyframe_insert('rotation_euler', frame=F_END)

def setup_lights_and_camera():
    # Lights
    bpy.ops.object.light_add(type='AREA', location=(0.5, -0.4, 0.5)); key = bpy.context.active_object
    key.data.energy = 2200; key.data.size = 0.45
    bpy.ops.object.light_add(type='SPOT', location=(-0.5, 0.4, 0.55)); rim = bpy.context.active_object
    rim.data.energy=1100; rim.data.spot_size=math.radians(60); rim.rotation_euler = Euler((math.radians(-60),0,math.radians(160)))

    # Camera path (cinematic but simple)
    bpy.ops.object.camera_add(location=(0.36,-0.56,0.12), rotation=(math.radians(85), 0, math.radians(20)))
    cam = bpy.context.active_object; cam.data.lens = 60
    def K(f, loc, rot):
        cam.location = Vector(loc); cam.keyframe_insert('location', frame=f)
        cam.rotation_euler = Euler(rot); cam.keyframe_insert('rotation_euler', frame=f)
    K(1, (0.36,-0.56,0.12), (math.radians(85),0,math.radians(20)))
    K(F_BITE-10, (0.28,-0.48,0.11), (math.radians(84),0,math.radians(18)))
    K(F_SENSING_START, (0.30,-0.50,0.11), (math.radians(85),0,math.radians(20)))
    K(F_ANTIDOTE_START+60, (0.40,-0.50,0.12), (math.radians(82),0,math.radians(24)))
    K(F_END, (0.50,-0.46,0.14), (math.radians(80),0,math.radians(28)))
    bpy.context.scene.camera = cam

# ========= TEXT LABELS (optional) =========
def add_floating_label(text, frame_in, frame_out, location=(0.0, -0.2, 0.2)):
    bpy.ops.object.text_add(location=location)
    t = bpy.context.active_object
    t.data.body = text
    t.data.extrude = 0.0
    t.data.size = 0.035
    t.rotation_euler = Euler((math.radians(90), 0, 0))
    # Fade in/out via alpha: convert to mesh + add emission material
    bpy.ops.object.convert(target='MESH')
    m = mat_emission((1,1,1,1), strength=1.5, name=f"Label_{text}")
    t.data.materials.append(m)
    # Animate visibility via viewport alpha trick: scale up/down
    t.scale = Vector((0.01,0.01,0.01)); t.keyframe_insert('scale', frame=frame_in-10)
    t.scale = Vector((1,1,1)); t.keyframe_insert('scale', frame=frame_in+5)
    t.scale = Vector((1,1,1)); t.keyframe_insert('scale', frame=frame_out-5)
    t.scale = Vector((0.01,0.01,0.01)); t.keyframe_insert('scale', frame=frame_out)
    return t

# ========= AUDIO (VSE) =========
def add_audio_to_vse(narration_rel, music_rel):
    sc = bpy.context.scene
    if not sc.sequence_editor:
        sc.sequence_editor_create()
    base = bpy.path.abspath("//") or os.getcwd()
    nar = os.path.join(base, narration_rel) if narration_rel else None
    mus = os.path.join(base, music_rel) if music_rel else None
    if nar and os.path.exists(nar):
        try:
            bpy.ops.sequencer.sound_strip_add(filepath=nar, frame_start=1, channel=1)
            print("Added narration:", nar)
        except Exception as e:
            print("Narration add failed:", e)
    else:
        print("Narration not found:", nar)
    if mus and os.path.exists(mus):
        try:
            bpy.ops.sequencer.sound_strip_add(filepath=mus, frame_start=1, channel=2)
            # Lower BG music
            for s in sc.sequence_editor.sequences_all:
                if s.type == 'SOUND' and os.path.basename(mus) in s.filepath:
                    s.volume = 0.35
            print("Added music:", mus)
        except Exception as e:
            print("Music add failed:", e)
    else:
        print("Music not found:", mus)

# ========= MAIN =========
def main():
    reset_scene()
    arm, strap, device, screen, port, bite, snake_path, snake_prof, venom_spheres, nano_spheres, antidote_wave = build_geometry()

    # Parent device bits to arm so subtle motion affects them
    strap.parent = arm; device.parent = arm; screen.parent = arm

    # Materials
    mapping_node, screen_mat = assign_materials(arm, strap, device, screen, venom_spheres, nano_spheres, antidote_wave)

    # Animations
    animate_snake(snake_path)
    animate_screen(screen_mat)
    animate_skin_hotspot(mapping_node)
    animate_nanodiamonds(nano_spheres, port, bite)
    animate_antidote_wave(antidote_wave)
    animate_arm_subtle(arm)
    setup_lights_and_camera()

    # Labels (brief technical captions)
    add_floating_label("Detection: Physiological Anomalies", F_DETECT_START, F_DETECT_START+120, location=(0.0,-0.22,0.18))
    add_floating_label("Nanodiamonds Deployed", F_ND_INJECT, F_ND_INJECT+120, location=(0.0,-0.22,0.18))
    add_floating_label("Quantum Sensing: Toxin Typing", F_SENSING_START, F_SENSING_START+140, location=(0.0,-0.22,0.18))
    add_floating_label("Tailored Antidote Delivery", F_ANTIDOTE_START, F_ANTIDOTE_START+160, location=(0.0,-0.22,0.18))
    add_floating_label("Amrisha — Smart. Quantum. Life-saving.", F_RECOVER, F_END-10, location=(-0.02,-0.22,0.18))

    # Audio (optional but automatic if files exist)
    add_audio_to_vse(NARRATION_FILE, MUSIC_FILE)

    print("Amrisha scene ready. Render → Render Animation (Ctrl+F12)")
    print("Output:", bpy.context.scene.render.filepath)

if __name__ == "__main__":
    main()
