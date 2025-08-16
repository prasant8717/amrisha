# Blender 3.x+ Python Script
# Builds a full 40s cinematic with primitives: arm, wearable, snake, venom & antidote effects
# Output: //amrisha.mp4 (1080p, 30 fps, Eevee)

import bpy
import math
from mathutils import Vector, Euler

# ----------------------------
# Basic scene setup
# ----------------------------
def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.render.engine = 'BLENDER_EEVEE'
    s = bpy.context.scene
    s.frame_start = 1
    s.frame_end = 1200  # 40s @ 30fps
    s.render.fps = 30
    s.render.resolution_x = 1920
    s.render.resolution_y = 1080
    s.render.resolution_percentage = 100
    s.eevee.use_bloom = True
    s.eevee.bloom_intensity = 0.08
    s.eevee.use_gtao = True
    s.eevee.use_ssr = True
    s.eevee.ssr_thickness = 0.2

    # Film / color management
    s.view_settings.look = 'Medium High Contrast'
    s.world.use_nodes = True
    wn = s.world.node_tree
    for n in wn.nodes:
        wn.nodes.remove(n)
    wout = wn.nodes.new("ShaderNodeOutputWorld")
    wbg = wn.nodes.new("ShaderNodeBackground")
    wbg.inputs[0].default_value = (0.02, 0.02, 0.03, 1.0)  # dark blueish
    wbg.inputs[1].default_value = 1.0
    wn.links.new(wbg.outputs['Background'], wout.inputs['Surface'])

    # Output to MP4 (H.264 + AAC)
    s.render.image_settings.file_format = 'FFMPEG'
    s.render.ffmpeg.format = 'MPEG4'
    s.render.ffmpeg.codec = 'H264'
    s.render.ffmpeg.constant_rate_factor = 'HIGH'
    s.render.ffmpeg.ffmpeg_preset = 'GOOD'
    s.render.ffmpeg.audio_codec = 'AAC'
    s.render.ffmpeg.audio_bitrate = 192
    s.render.filepath = "//amrisha.mp4"

def set_key(obj, frame, loc=None, rot=None, scale=None, data_path=None, value=None):
    if loc is not None:
        obj.location = Vector(loc)
        obj.keyframe_insert("location", frame=frame)
    if rot is not None:
        obj.rotation_euler = Euler(rot)
        obj.keyframe_insert("rotation_euler", frame=frame)
    if scale is not None:
        obj.scale = Vector(scale)
        obj.keyframe_insert("scale", frame=frame)
    if data_path is not None:
        obj.keyframe_insert(data_path=data_path, frame=frame)

# ----------------------------
# Materials
# ----------------------------
def make_skin_material(name="SkinMat"):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    for n in nt.nodes:
        if n.name != "Material Output":
            nt.nodes.remove(n)
    out = nt.nodes["Material Output"]

    # Nodes
    principled = nt.nodes.new("ShaderNodeBsdfPrincipled")
    principled.inputs["Base Color"].default_value = (0.85, 0.63, 0.53, 1)
    principled.inputs["Subsurface"].default_value = 0.2
    principled.inputs["Roughness"].default_value = 0.6

    # Venom mask (spherical gradient from bite Empty)
    texcoord = nt.nodes.new("ShaderNodeTexCoord")
    obj_in = nt.nodes.new("ShaderNodeObjectInfo")  # use Object location of an Empty as center
    mapping = nt.nodes.new("ShaderNodeMapping")
    mapping.vector_type = 'POINT'
    grad = nt.nodes.new("ShaderNodeTexGradient")
    grad.gradient_type = 'SPHERICAL'
    ramp_red = nt.nodes.new("ShaderNodeValToRGB")
    ramp_red.color_ramp.elements[0].position = 0.35
    ramp_red.color_ramp.elements[1].position = 0.6
    # Emission (red veins)
    emit_red = nt.nodes.new("ShaderNodeEmission")
    emit_red.inputs['Color'].default_value = (1.0, 0.1, 0.05, 1)
    emit_red.inputs['Strength'].default_value = 2.0
    mix_skin_red = nt.nodes.new("ShaderNodeMixShader")

    # Antidote mask (spherical from device Empty)
    mapping2 = nt.nodes.new("ShaderNodeMapping")
    mapping2.vector_type = 'POINT'
    grad2 = nt.nodes.new("ShaderNodeTexGradient")
    grad2.gradient_type = 'SPHERICAL'
    ramp_blue = nt.nodes.new("ShaderNodeValToRGB")
    ramp_blue.color_ramp.elements[0].position = 0.35
    ramp_blue.color_ramp.elements[1].position = 0.6
    emit_blue = nt.nodes.new("ShaderNodeEmission")
    emit_blue.inputs['Color'].default_value = (0.1, 0.6, 1.0, 1)
    emit_blue.inputs['Strength'].default_value = 2.5
    mix_after_blue = nt.nodes.new("ShaderNodeMixShader")

    # Links (Venom branch)
    nt.links.new(texcoord.outputs['Object'], mapping.inputs['Vector'])
    nt.links.new(mapping.outputs['Vector'], grad.inputs['Vector'])
    nt.links.new(grad.outputs['Fac'], ramp_red.inputs['Fac'])
    nt.links.new(principled.outputs['BSDF'], mix_skin_red.inputs[1])
    nt.links.new(emit_red.outputs['Emission'], mix_skin_red.inputs[2])
    nt.links.new(ramp_red.outputs['Color'], mix_skin_red.inputs['Fac'])

    # Links (Antidote branch stacked after)
    nt.links.new(mapping2.outputs['Vector'], grad2.inputs['Vector'])
    nt.links.new(grad2.outputs['Fac'], ramp_blue.inputs['Fac'])
    nt.links.new(mix_skin_red.outputs['Shader'], mix_after_blue.inputs[1])
    nt.links.new(emit_blue.outputs['Emission'], mix_after_blue.inputs[2])
    nt.links.new(ramp_blue.outputs['Color'], mix_after_blue.inputs['Fac'])

    nt.links.new(mix_after_blue.outputs['Shader'], out.inputs['Surface'])

    # Expose mappings for animation via custom properties we’ll drive with Empties
    return mat, mapping, mapping2

def make_plastic_mat(color=(0.1,0.1,0.1,1.0), name="Plastic"):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    bsdf.inputs['Base Color'].default_value = color
    bsdf.inputs['Specular'].default_value = 0.5
    bsdf.inputs['Roughness'].default_value = 0.3
    return mat

def make_emission_mat(color=(0.1,0.7,1.0,1.0), strength=10.0, name="Glow"):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    for n in nt.nodes:
        if n.name != "Material Output":
            nt.nodes.remove(n)
    out = nt.nodes["Material Output"]
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs['Color'].default_value = color
    em.inputs['Strength'].default_value = strength
    nt.links.new(em.outputs['Emission'], out.inputs['Surface'])
    return mat

# ----------------------------
# Build geometry
# ----------------------------
def build_armature():
    # Arm (cylinder)
    bpy.ops.mesh.primitive_cylinder_add(radius=0.12, depth=0.45, location=(0,0,0))
    arm = bpy.context.active_object
    arm.name = "Arm"
    arm.rotation_euler = Euler((math.radians(90), 0, 0))
    arm.location = Vector((0, 0, 0.0))

    # Wearable strap (torus)
    bpy.ops.mesh.primitive_torus_add(major_radius=0.12, minor_radius=0.02, location=(0.0, 0.0, 0.05))
    strap = bpy.context.active_object
    strap.name = "Strap"
    strap.rotation_euler = Euler((math.radians(90), 0, 0))

    # Device body (cube)
    bpy.ops.mesh.primitive_cube_add(size=0.06, location=(0.11, 0.0, 0.05))
    device = bpy.context.active_object
    device.name = "Device"
    device.rotation_euler = Euler((0, math.radians(20), 0))

    # Small screen (plane with emission)
    bpy.ops.mesh.primitive_plane_add(size=0.045, location=(0.14, 0.0, 0.05))
    screen = bpy.context.active_object
    screen.name = "Screen"
    screen.rotation_euler = Euler((0, math.radians(20), 0))

    # Snake: a curve with bevel to look tubular
    bpy.ops.curve.primitive_bezier_curve_add(location=(-0.6, -0.4, 0.06))
    curve = bpy.context.active_object
    curve.name = "SnakePath"
    # Shape the curve control points a bit
    csp = curve.data.splines[0].bezier_points
    csp[0].co = Vector((-0.6, -0.4, 0.06))
    csp[0].handle_left = csp[0].co + Vector((-0.2, -0.1, 0.0))
    csp[0].handle_right = csp[0].co + Vector((0.2, 0.2, 0.0))
    csp[1].co = Vector((0.08, 0.0, 0.06))  # near bite
    csp[1].handle_left = csp[1].co + Vector((-0.2, -0.2, 0.0))
    csp[1].handle_right = csp[1].co + Vector((0.2, 0.2, 0.0))

    # Bevel for thickness
    bpy.ops.curve.primitive_bezier_circle_add(radius=0.015, location=(0,0,0))
    profile = bpy.context.active_object
    profile.name = "SnakeProfile"
    curve.data.bevel_object = profile
    curve.data.resolution_u = 24

    # Empties for shader origins
    bpy.ops.object.empty_add(type='PLAIN_AXES', location=(0.08, 0.0, 0.06))  # bite center on arm
    empty_bite = bpy.context.active_object
    empty_bite.name = "Empty_Bite"
    bpy.ops.object.empty_add(type='PLAIN_AXES', location=(0.11, 0.0, 0.05))  # device center
    empty_device = bpy.context.active_object
    empty_device.name = "Empty_Device"

    return arm, strap, device, screen, curve, profile, empty_bite, empty_device

# ----------------------------
# Assign materials & node hookups
# ----------------------------
def assign_materials(arm, strap, device, screen, empty_bite, empty_device):
    skin_mat, map_venom, map_antidote = make_skin_material()
    arm.data.materials.append(skin_mat)

    strap.data.materials.append(make_plastic_mat((0.08,0.08,0.08,1),'StrapPlastic'))
    device.data.materials.append(make_plastic_mat((0.12,0.12,0.12,1),'DeviceBody'))
    screen.data.materials.append(make_emission_mat((0.1,0.8,1.0,1), strength=5.0, name="ScreenGlow"))

    # Connect Object coordinates for venom: use empty_bite as reference
    nt = skin_mat.node_tree
    texcoord = None
    for n in nt.nodes:
        if n.bl_idname == 'ShaderNodeTexCoord':
            texcoord = n
            break
    # Set object for texture coordinate by using Object output via mapping -> gradient
    # Here we simply parent the Mappings to empties by animating their scale/translation
    # Trick: we’ll animate Mapping node scale to simulate radius growth/shrink.

    # Put mappings at bite & device locations (via translation)
    map_venom.inputs['Location'].default_value = empty_bite.location
    map_antidote.inputs['Location'].default_value = empty_device.location

    return skin_mat, map_venom, map_antidote

# ----------------------------
# Lighting & camera
# ----------------------------
def setup_lights():
    # Key light (Area)
    bpy.ops.object.light_add(type='AREA', location=(0.5, -0.4, 0.5))
    key = bpy.context.active_object
    key.data.energy = 2000
    key.data.size = 0.4

    # Rim light
    bpy.ops.object.light_add(type='SPOT', location=(-0.5, 0.4, 0.5))
    rim = bpy.context.active_object
    rim.data.energy = 1000
    rim.data.spot_size = math.radians(60)
    rim.data.shadow_soft_size = 0.2
    rim.rotation_euler = Euler((math.radians(-60), math.radians(0), math.radians(160)))

def setup_camera():
    bpy.ops.object.camera_add(location=(0.35, -0.55, 0.12), rotation=(math.radians(85), 0, math.radians(20)))
    cam = bpy.context.active_object
    cam.data.lens = 60
    # Camera motion (keyframes over the timeline)
    set_key(cam, 1, loc=(0.35, -0.55, 0.12), rot=(math.radians(85), 0, math.radians(20)))
    set_key(cam, 210, loc=(0.25, -0.45, 0.10), rot=(math.radians(83), 0, math.radians(18)))
    set_key(cam, 510, loc=(0.30, -0.50, 0.11), rot=(math.radians(85), 0, math.radians(20)))
    set_key(cam, 810, loc=(0.40, -0.52, 0.12), rot=(math.radians(82), 0, math.radians(25)))
    set_key(cam, 1200, loc=(0.50, -0.48, 0.13), rot=(math.radians(80), 0, math.radians(30)))
    bpy.context.scene.camera = cam

# ----------------------------
# Snake animation (bevel factor “growth”)
# ----------------------------
def animate_snake(curve, profile):
    # Animate the Bevel Start/End to make the snake slither in
    c = curve.data
    c.fill_mode = 'FULL'
    c.bevel_object = profile
    c.bevel_factor_mapping_start = 'SPLINE'
    c.bevel_factor_mapping_end = 'SPLINE'
    c.use_map_taper = False

    # Start invisible
    c.bevel_factor_start = 1.0
    c.bevel_factor_end = 1.0
    c.keyframe_insert('bevel_factor_start', frame=1)
    c.keyframe_insert('bevel_factor_end', frame=1)

    # Enter (frames 60..180)
    c.bevel_factor_start = 0.0
    c.bevel_factor_end = 1.0
    c.keyframe_insert('bevel_factor_start', frame=180)
    c.keyframe_insert('bevel_factor_end', frame=180)

    # Strike pose around 210 (hold)
    c.keyframe_insert('bevel_factor_start', frame=210)
    c.keyframe_insert('bevel_factor_end', frame=210)

    # Retreat (frames 900..1100)
    c.keyframe_insert('bevel_factor_start', frame=900)
    c.keyframe_insert('bevel_factor_end', frame=900)
    c.bevel_factor_start = 1.0
    c.bevel_factor_end = 1.0
    c.keyframe_insert('bevel_factor_start', frame=1100)
    c.keyframe_insert('bevel_factor_end', frame=1100)

# ----------------------------
# Venom & Antidote timing (animate Mapping node scale)
# ----------------------------
def animate_chemistry(mapping_venom, mapping_antidote):
    # Venom spread: grow from small radius (frames 210..510)
    # Use Mapping Scale as inverse radius: small scale -> larger visible radius
    # Start: tight (0.3,0.3,0.3) -> End: broad (0.02,0.02,0.02)
    mv = mapping_venom
    mv.inputs['Scale'].default_value = (0.3, 0.3, 0.3)
    mv.keyframe_insert(data_path='inputs[3].default_value', frame=210)  # Scale socket index is 3
    mv.inputs['Scale'].default_value = (0.02, 0.02, 0.02)
    mv.keyframe_insert(data_path='inputs[3].default_value', frame=510)

    # Antidote release: grow from device (frames 510..810)
    ma = mapping_antidote
    ma.inputs['Scale'].default_value = (0.3, 0.3, 0.3)
    ma.keyframe_insert(data_path='inputs[3].default_value', frame=510)
    ma.inputs['Scale'].default_value = (0.015, 0.015, 0.015)
    ma.keyframe_insert(data_path='inputs[3].default_value', frame=810)

    # Recovery: fade both back out by shrinking venom radius (make it huge, thus threshold off)
    mv.inputs['Scale'].default_value = (2.0, 2.0, 2.0)
    mv.keyframe_insert(data_path='inputs[3].default_value', frame=1000)
    ma.inputs['Scale'].default_value = (2.0, 2.0, 2.0)
    ma.keyframe_insert(data_path='inputs[3].default_value', frame=1000)

# ----------------------------
# Screen status & holo UI
# ----------------------------
def animate_screen(screen):
    # Screen glow: idle -> alert red -> blue active -> settle
    mat = screen.data.materials[0]
    nt = mat.node_tree
    em = None
    for n in nt.nodes:
        if n.bl_idname == 'ShaderNodeEmission':
            em = n
            break
    # Idle cyan
    em.inputs['Color'].default_value = (0.1, 0.8, 1.0, 1)
    em.inputs['Strength'].default_value = 3.0
    em.inputs['Color'].keyframe_insert('default_value', frame=1)
    em.inputs['Strength'].keyframe_insert('default_value', frame=1)

    # Threat (around bite): flash red at 210..240
    em.inputs['Color'].default_value = (1.0, 0.15, 0.1, 1)
    em.inputs['Strength'].default_value = 6.0
    em.inputs['Color'].keyframe_insert('default_value', frame=210)
    em.inputs['Strength'].keyframe_insert('default_value', frame=210)
    em.inputs['Color'].keyframe_insert('default_value', frame=240)
    em.inputs['Strength'].keyframe_insert('default_value', frame=240)

    # Antidote active (510..810): blue strong
    em.inputs['Color'].default_value = (0.15, 0.6, 1.0, 1)
    em.inputs['Strength'].default_value = 9.0
    em.inputs['Color'].keyframe_insert('default_value', frame=510)
    em.inputs['Strength'].keyframe_insert('default_value', frame=510)
    em.inputs['Color'].keyframe_insert('default_value', frame=810)
    em.inputs['Strength'].keyframe_insert('default_value', frame=810)

    # Settle (end)
    em.inputs['Color'].default_value = (0.1, 0.8, 1.0, 1)
    em.inputs['Strength'].default_value = 4.0
    em.inputs['Color'].keyframe_insert('default_value', frame=1100)
    em.inputs['Strength'].keyframe_insert('default_value', frame=1100)

def add_holo_ui():
    # Floating plane above device with blue emission text effect
    bpy.ops.mesh.primitive_plane_add(size=0.08, location=(0.11, 0.0, 0.10))
    holo = bpy.context.active_object
    holo.name = "HoloUI"
    holo_mat = make_emission_mat((0.2, 0.7, 1.0, 1), strength=2.5, name="HoloUI")
    holo.data.materials.append(holo_mat)
    # Animate visibility (fade in at 520, out at 800)
    holo.hide_render = True
    holo.keyframe_insert("hide_render", frame=1)
    holo.hide_render = False
    holo.keyframe_insert("hide_render", frame=520)
    holo.hide_render = False
    holo.keyframe_insert("hide_render", frame=800)
    holo.hide_render = True
    holo.keyframe_insert("hide_render", frame=820)

# ----------------------------
# Main build
# ----------------------------
def main():
    reset_scene()
    arm, strap, device, screen, curve, profile, empty_bite, empty_device = build_armature()

    # Materials
    skin_mat, map_venom, map_antidote = assign_materials(arm, strap, device, screen, empty_bite, empty_device)

    # Lighting & camera
    setup_lights()
    setup_camera()

    # Animate snake in/out
    animate_snake(curve, profile)

    # Animate venom & antidote masks via Mapping scale
    animate_chemistry(map_venom, map_antidote)

    # Animate screen status + holo
    animate_screen(screen)
    add_holo_ui()

    # Final touches: parent strap/device/screen to arm so they move together (if needed later)
    strap.parent = arm
    device.parent = arm
    screen.parent = arm

    # Slight arm sway for subtle life
    set_key(arm, 1, rot=(math.radians(90), 0, math.radians(-2)))
    set_key(arm, 600, rot=(math.radians(90), 0, math.radians(2)))
    set_key(arm, 1200, rot=(math.radians(90), 0, math.radians(-2)))

    # Done
    print("Scene constructed. To render: Render > Render Animation (Ctrl+F12).")
    print("Output:", bpy.context.scene.render.filepath)

if __name__ == "__main__":
    main()
