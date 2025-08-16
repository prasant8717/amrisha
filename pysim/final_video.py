# Blender combined animation + audio script (simpler primitives, cinematic)
# Blender 3.x+ recommended.
# Paste into Blender Scripting editor and Run.
import bpy, os, math
from mathutils import Vector, Euler

# ---------------- CONFIG ----------------
OUTNAME = "amrisha.mp4"
FPS = 30
DURATION_SEC = 40
TOTAL_FRAMES = FPS * DURATION_SEC
RES_X = 1920
RES_Y = 1080

NARRATION_FILE = "amrisha.wav"   # place in same folder as .blend (or full path)
MUSIC_FILE = "music.mp3"           # place in same folder as .blend (or full path)

# ---------------- helpers ----------------
def clear_scene_and_setup():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_EEVEE'
    sc.frame_start = 1
    sc.frame_end = TOTAL_FRAMES
    sc.render.fps = FPS
    sc.render.resolution_x = RES_X
    sc.render.resolution_y = RES_Y
    sc.render.resolution_percentage = 100

    # Eevee tweaks
    sc.eevee.use_bloom = True
    sc.eevee.bloom_intensity = 0.06
    sc.eevee.use_gtao = True
    sc.eevee.use_ssr = True
    sc.view_settings.look = 'Medium High Contrast'

    # world background
    sc.world.use_nodes = True
    wn = sc.world.node_tree
    for n in wn.nodes: wn.nodes.remove(n)
    node_out = wn.nodes.new("ShaderNodeOutputWorld")
    node_bg = wn.nodes.new("ShaderNodeBackground")
    node_bg.inputs[0].default_value = (0.02, 0.02, 0.03, 1.0)
    node_bg.inputs[1].default_value = 1.0
    wn.links.new(node_bg.outputs['Background'], node_out.inputs['Surface'])

    # output format
    sc.render.image_settings.file_format = 'FFMPEG'
    sc.render.ffmpeg.format = 'MPEG4'
    sc.render.ffmpeg.codec = 'H264'
    sc.render.ffmpeg.constant_rate_factor = 'HIGH'
    sc.render.ffmpeg.ffmpeg_preset = 'GOOD'
    sc.render.ffmpeg.audio_codec = 'AAC'
    sc.render.ffmpeg.audio_bitrate = 192
    sc.render.filepath = "//" + OUTNAME

def set_key_transform(obj, frame, loc=None, rot=None, scale=None):
    if loc is not None:
        obj.location = Vector(loc)
        obj.keyframe_insert(data_path="location", frame=frame)
    if rot is not None:
        obj.rotation_euler = Euler(rot)
        obj.keyframe_insert(data_path="rotation_euler", frame=frame)
    if scale is not None:
        obj.scale = Vector(scale)
        obj.keyframe_insert(data_path="scale", frame=frame)

# ---------------- materials ----------------
def skin_material():
    mat = bpy.data.materials.new("Skin")
    mat.use_nodes = True
    nt = mat.node_tree
    # clear nodes except output
    for n in list(nt.nodes):
        if n.type != 'OUTPUT_MATERIAL':
            nt.nodes.remove(n)
    out = nt.nodes.get("Material Output")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = (0.86, 0.68, 0.56, 1.0)
    bsdf.inputs["Subsurface"].default_value = 0.15
    bsdf.inputs["Roughness"].default_value = 0.6

    # gradient for venom/antidote mixing (spherical)
    texcoord = nt.nodes.new("ShaderNodeTexCoord")
    mapping = nt.nodes.new("ShaderNodeMapping")
    grad = nt.nodes.new("ShaderNodeTexGradient"); grad.gradient_type = 'SPHERICAL'
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.35
    ramp.color_ramp.elements[1].position = 0.60

    emit_red = nt.nodes.new("ShaderNodeEmission"); emit_red.inputs['Color'].default_value = (1.0,0.08,0.06,1); emit_red.inputs['Strength'].default_value = 2.4
    emit_blue = nt.nodes.new("ShaderNodeEmission"); emit_blue.inputs['Color'].default_value = (0.08,0.55,1.0,1); emit_blue.inputs['Strength'].default_value = 3.0

    mix1 = nt.nodes.new("ShaderNodeMixShader")
    mix2 = nt.nodes.new("ShaderNodeMixShader")

    # links
    nt.links.new(texcoord.outputs['Object'], mapping.inputs['Vector'])
    nt.links.new(mapping.outputs['Vector'], grad.inputs['Vector'])
    nt.links.new(grad.outputs['Fac'], ramp.inputs['Fac'])
    nt.links.new(bsdf.outputs['BSDF'], mix1.inputs[1])
    nt.links.new(emit_red.outputs['Emission'], mix1.inputs[2])
    nt.links.new(ramp.outputs['Color'], mix1.inputs['Fac'])
    nt.links.new(mix1.outputs['Shader'], mix2.inputs[1])
    nt.links.new(emit_blue.outputs['Emission'], mix2.inputs[2])
    nt.links.new(ramp.outputs['Color'], mix2.inputs['Fac'])
    nt.links.new(mix2.outputs['Shader'], out.inputs['Surface'])

    # expose mapping node for animation (return it)
    return mat, mapping

def plastic_material(col=(0.12,0.12,0.12,1.0), name="Plastic"):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs['Base Color'].default_value = col
    bsdf.inputs['Roughness'].default_value = 0.25
    bsdf.inputs['Specular'].default_value = 0.5
    return mat

def emission_material(color=(0.08,0.7,1.0,1.0), strength=6.0, name="Emit"):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    # clear except output
    nt = mat.node_tree
    for n in list(nt.nodes):
        if n.type != 'OUTPUT_MATERIAL':
            nt.nodes.remove(n)
    out = nt.nodes.get("Material Output")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs['Color'].default_value = color
    em.inputs['Strength'].default_value = strength
    nt.links.new(em.outputs['Emission'], out.inputs['Surface'])
    return mat

# ---------------- geometry ----------------
def build_primitives():
    # Arm: cylinder rotated to lie horizontally
    bpy.ops.mesh.primitive_cylinder_add(radius=0.12, depth=0.45, location=(0,0,0))
    arm = bpy.context.active_object
    arm.name = "Arm"
    arm.rotation_euler = Euler((math.radians(90), 0, 0))
    arm.location = Vector((0, 0, 0.0))

    # Strap (torus)
    bpy.ops.mesh.primitive_torus_add(major_radius=0.12, minor_radius=0.02, location=(0.0, 0.0, 0.05))
    strap = bpy.context.active_object; strap.name = "Strap"; strap.rotation_euler = Euler((math.radians(90),0,0))

    # Device body (cube)
    bpy.ops.mesh.primitive_cube_add(size=0.06, location=(0.11, 0.0, 0.05))
    device = bpy.context.active_object; device.name = "Device"; device.rotation_euler = Euler((0, math.radians(20), 0))

    # Screen (plane)
    bpy.ops.mesh.primitive_plane_add(size=0.045, location=(0.14, 0.0, 0.05))
    screen = bpy.context.active_object; screen.name = "Screen"; screen.rotation_euler = Euler((0, math.radians(20), 0))

    # Snake: simple curve + bevel circle to make tube
    bpy.ops.curve.primitive_bezier_curve_add(location=(-0.6, -0.4, 0.06))
    curve = bpy.context.active_object; curve.name = "SnakePath"
    points = curve.data.splines[0].bezier_points
    points[0].co = Vector((-0.6, -0.4, 0.06))
    points[0].handle_left = points[0].co + Vector((-0.2, -0.1, 0))
    points[0].handle_right = points[0].co + Vector((0.2, 0.2, 0))
    points[1].co = Vector((0.08, 0.0, 0.06))
    points[1].handle_left = points[1].co + Vector((-0.2, -0.2, 0))
    points[1].handle_right = points[1].co + Vector((0.2, 0.2, 0))
    bpy.ops.curve.primitive_bezier_circle_add(radius=0.015, location=(0,0,0))
    profile = bpy.context.active_object; profile.name = "SnakeProfile"
    curve.data.bevel_object = profile
    curve.data.resolution_u = 24

    # Empties for shader origins
    bpy.ops.object.empty_add(type='PLAIN_AXES', location=(0.08, 0.0, 0.06)); empty_bite = bpy.context.active_object; empty_bite.name = "Empty_Bite"
    bpy.ops.object.empty_add(type='PLAIN_AXES', location=(0.11, 0.0, 0.05)); empty_device = bpy.context.active_object; empty_device.name = "Empty_Device"

    return arm, strap, device, screen, curve, profile, empty_bite, empty_device

# ---------------- animation helpers ----------------
def animate_camera_and_arm():
    # camera
    bpy.ops.object.camera_add(location=(0.35, -0.55, 0.12), rotation=(math.radians(85), 0, math.radians(20)))
    cam = bpy.context.active_object
    cam.name = "Camera"
    cam.data.lens = 60
    # keyframes (simple cinematic pans over timeline)
    set_key_transform(cam, 1, loc=(0.35, -0.55, 0.12), rot=(math.radians(85), 0, math.radians(20)))
    set_key_transform(cam, 220, loc=(0.25, -0.45, 0.10), rot=(math.radians(83), 0, math.radians(18)))
    set_key_transform(cam, 520, loc=(0.30, -0.50, 0.11), rot=(math.radians(85), 0, math.radians(20)))
    set_key_transform(cam, 820, loc=(0.40, -0.52, 0.12), rot=(math.radians(82), 0, math.radians(25)))
    set_key_transform(cam, TOTAL_FRAMES, loc=(0.50, -0.48, 0.13), rot=(math.radians(80), 0, math.radians(30)))
    bpy.context.scene.camera = cam

def animate_snake(curve):
    # use bevel factor to grow snake in/out
    cdata = curve.data
    cdata.bevel_factor_start = 1.0; cdata.bevel_factor_end = 1.0
    cdata.keyframe_insert('bevel_factor_start', frame=1); cdata.keyframe_insert('bevel_factor_end', frame=1)
    cdata.bevel_factor_start = 0.0; cdata.bevel_factor_end = 1.0
    cdata.keyframe_insert('bevel_factor_start', frame=180); cdata.keyframe_insert('bevel_factor_end', frame=180)
    # bite moment (hold)
    cdata.keyframe_insert('bevel_factor_start', frame=210); cdata.keyframe_insert('bevel_factor_end', frame=210)
    # retreat
    cdata.keyframe_insert('bevel_factor_start', frame=900); cdata.keyframe_insert('bevel_factor_end', frame=900)
    cdata.bevel_factor_start = 1.0; cdata.bevel_factor_end = 1.0
    cdata.keyframe_insert('bevel_factor_start', frame=1100); cdata.keyframe_insert('bevel_factor_end', frame=1100)

def animate_device_screen(screen):
    # animate screen emission color to flash and then pulse blue
    mat = screen.data.materials[0]
    nt = mat.node_tree
    em_node = None
    for n in nt.nodes:
        if n.type == 'EMISSION':
            em_node = n
            break
    if not em_node:
        return
    # idle
    em_node.inputs['Color'].default_value = (0.1,0.8,1.0,1); em_node.inputs['Strength'].default_value = 3.0
    em_node.inputs['Color'].keyframe_insert('default_value', frame=1); em_node.inputs['Strength'].keyframe_insert('default_value', frame=1)
    # flash red at bite
    em_node.inputs['Color'].default_value = (1.0,0.12,0.08,1); em_node.inputs['Strength'].default_value = 6.5
    em_node.inputs['Color'].keyframe_insert('default_value', frame=210); em_node.inputs['Strength'].keyframe_insert('default_value', frame=210)
    em_node.inputs['Color'].default_value = (0.1,0.8,1.0,1); em_node.inputs['Strength'].default_value = 3.5
    em_node.inputs['Color'].keyframe_insert('default_value', frame=260); em_node.inputs['Strength'].keyframe_insert('default_value', frame=260)
    # Antidote phase strong blue
    em_node.inputs['Color'].default_value = (0.1,0.6,1.0,1); em_node.inputs['Strength'].default_value = 9.0
    em_node.inputs['Color'].keyframe_insert('default_value', frame=510); em_node.inputs['Strength'].keyframe_insert('default_value', frame=510)
    em_node.inputs['Color'].keyframe_insert('default_value', frame=810); em_node.inputs['Strength'].keyframe_insert('default_value', frame=810)
    # settle
    em_node.inputs['Color'].default_value = (0.1,0.8,1.0,1); em_node.inputs['Strength'].default_value = 4.0
    em_node.inputs['Color'].keyframe_insert('default_value', frame=1000); em_node.inputs['Strength'].keyframe_insert('default_value', frame=1000)

def animate_venom_and_antidote(mapping_node):
    # mapping_node.inputs['Scale'] controls size of spherical gradient used in material
    # small scale => tight hotspot; animate to simulate spread and then antidote override
    # We'll animate scale vector (inputs[3].default_value)
    try:
        # initial (small sphere)
        mapping_node.inputs['Scale'].default_value = (0.35,0.35,0.35)
        mapping_node.inputs['Scale'].keyframe_insert(data_path='default_value', frame=210)
        # venom spread (grow)
        mapping_node.inputs['Scale'].default_value = (0.02,0.02,0.02)
        mapping_node.inputs['Scale'].keyframe_insert(data_path='default_value', frame=510)
        # after antidote, push scale large to fade effect
        mapping_node.inputs['Scale'].default_value = (2.0,2.0,2.0)
        mapping_node.inputs['Scale'].keyframe_insert(data_path='default_value', frame=1000)
    except Exception as e:
        print("Mapping animation error (may be node type differences):", e)

# ---------------- VSE audio ----------------
def add_audio_to_vse(narration_rel, music_rel):
    scene = bpy.context.scene
    if not scene.sequence_editor:
        scene.sequence_editor_create()
    base_dir = bpy.path.abspath("//") or os.getcwd()
    narration_path = os.path.join(base_dir, narration_rel) if narration_rel else None
    music_path = os.path.join(base_dir, music_rel) if music_rel else None
    if narration_path and os.path.exists(narration_path):
        try:
            bpy.ops.sequencer.sound_strip_add(filepath=narration_path, frame_start=1, channel=1)
            print("Added narration:", narration_path)
        except Exception as e:
            print("Failed to add narration:", e)
    else:
        print("Narration not found:", narration_path)
    if music_path and os.path.exists(music_path):
        try:
            bpy.ops.sequencer.sound_strip_add(filepath=music_path, frame_start=1, channel=2)
            # lower music volume
            for s in scene.sequence_editor.sequences_all:
                if s.type == 'SOUND' and os.path.basename(music_path) in s.filepath:
                    s.volume = 0.35
            print("Added music:", music_path)
        except Exception as e:
            print("Failed to add music:", e)
    else:
        print("Music not found:", music_path)

# ---------------- main assembly ----------------
def main():
    clear_scene_and_setup()

    # Build geometry
    arm, strap, device, screen, curve, profile, empty_bite, empty_device = build_primitives()

    # Materials
    skin_mat, mapping_node = skin_material()
    arm.data.materials.append(skin_mat)
    strap.data.materials.append(plastic_material((0.06,0.06,0.06,1), 'Strap'))
    device.data.materials.append(plastic_material((0.12,0.12,0.12,1), 'Device'))
    screen.data.materials.append(emission_material((0.1,0.8,1,1), strength=5.0, name="ScreenEmit"))

    # Parenting so device follows arm
    strap.parent = arm
    device.parent = arm
    screen.parent = arm

    # Animate components
    animate_camera_and_arm()
    animate_snake(curve)
    animate_device_screen(screen)
    animate_venom_and_antidote(mapping_node)

    # small arm sway to add life
    arm.rotation_euler = Euler((math.radians(90),0,math.radians(-2))); arm.keyframe_insert('rotation_euler', frame=1)
    arm.rotation_euler = Euler((math.radians(90),0,math.radians(2))); arm.keyframe_insert('rotation_euler', frame=600)
    arm.rotation_euler = Euler((math.radians(90),0,math.radians(-2))); arm.keyframe_insert('rotation_euler', frame=TOTAL_FRAMES)

    # Add audio (if files present)
    add_audio_to_vse(NARRATION_FILE, MUSIC_FILE)

    print("Setup complete. Render settings:")
    print("  Output file (relative to blend):", bpy.context.scene.render.filepath)
    print("  Frames:", bpy.context.scene.frame_start, "-", bpy.context.scene.frame_end)
    print("To render: Render -> Render Animation (Ctrl+F12)")

if __name__ == "__main__":
    main()
