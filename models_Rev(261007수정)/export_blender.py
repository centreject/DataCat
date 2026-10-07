"""Rev D 조립품을 Blender 파일(.blend)과 glTF(.glb)로 내보낸다.

  python export_blender.py   →  out/blender/DataCat_doorbell_RevD.blend / .glb
실제 크기(1 Blender 단위 = 1 m, 화면 표시는 mm), Z 위, 정면 = Blender Front 뷰(-Y 방향)
"""
import math, os, tempfile
import cadquery as cq
import bpy
import model as M

OUT = 'out/blender'
os.makedirs(OUT, exist_ok=True)
tmp = tempfile.mkdtemp()

parts, comps = M.build_all()

# (이름, 모양, 색 RGBA, 컬렉션, 재질 종류)
P, R, K = '1_출력부품', '2_실제부품(참고)', '3_비워둔공간'
items = [
    ('01_front_shell', parts['01_front_shell'], (0.93, 0.91, 0.87, 1), P, 'plastic'),
    ('02_lcd_pi_chassis', parts['02_lcd_pi_chassis'], (0.49, 0.51, 0.54, 1), P, 'plastic'),
    ('03_wall_plate', parts['03_wall_plate'], (0.85, 0.83, 0.78, 1), P, 'plastic'),
    ('04_black_visor', parts['04_black_visor'], (0.02, 0.02, 0.025, 1), P, 'gloss'),
    ('05_led_light_pipe', parts['05_led_light_pipe'], (1.0, 0.75, 0.4, 1), P, 'glow'),
    ('REF_raspberry_pi_4', comps['Raspberry Pi 4'], (0.12, 0.38, 0.2, 1), R, 'pcb'),
    ('REF_usbc_plug', comps['USB-C L형 플러그'], (0.05, 0.05, 0.05, 1), R, 'plastic'),
    ('REF_hdmi_lcd_3p5in', comps['3.5인치 HDMI LCD'], (0.03, 0.03, 0.03, 1), R, 'plastic'),
    ('REF_lcd_screen', comps['_LCD 화면'], (0.04, 0.06, 0.09, 1), R, 'screen'),
    ('REF_camera_board', comps['_cam_board'], (0.12, 0.38, 0.2, 1), R, 'pcb'),
    ('REF_camera_lens', comps['_cam_lens'], (0.02, 0.02, 0.02, 1), R, 'gloss'),
    ('REF_tof_board', comps['_tof_board'], (0.6, 0.08, 0.1, 1), R, 'pcb'),
    ('REF_tof_sensor', comps['_tof_sensor'], (0.02, 0.02, 0.02, 1), R, 'gloss'),
    ('REF_usb_mic_dongle', comps['USB 마이크 동글'], (0.05, 0.05, 0.05, 1), R, 'plastic'),
    ('REF_usb_speaker_plug', comps['USB 스피커 플러그'], (0.05, 0.05, 0.05, 1), R, 'plastic'),
    ('REF_usb_speaker_board', comps['USB 스피커 보드'], (0.12, 0.22, 0.55, 1), R, 'pcb'),
    ('REF_speaker_28mm', comps['USB 스피커 유닛 ø28'], (0.12, 0.12, 0.13, 1), R, 'metal'),
    ('REF_button_16mm', comps['16mm 호출벨'], (0.8, 0.8, 0.82, 1), R, 'metal'),
    ('REF_status_led', comps['상태 LED'], (1.0, 0.7, 0.3, 1), R, 'glow'),
    ('KEEP_hdmi_fpc_cable', comps['HDMI FPC 케이블(공간)'], (0.95, 0.55, 0.15, 0.35), K, 'ghost'),
    ('KEEP_gpio27_40_wiring', comps['GPIO 27~40 배선(공간)'], (0.95, 0.55, 0.15, 0.35), K, 'ghost'),
]

# ── 새 장면 ──
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.unit_settings.system = 'METRIC'
sc.unit_settings.length_unit = 'MILLIMETERS'
sc.unit_settings.scale_length = 1.0

cols = {}
for name in (P, R, K):
    c = bpy.data.collections.new(name)
    sc.collection.children.link(c)
    cols[name] = c


def material(name, rgba, kind):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = rgba
    rough = {'plastic': 0.6, 'gloss': 0.08, 'pcb': 0.5, 'metal': 0.3, 'glow': 0.4, 'screen': 0.2, 'ghost': 0.6}[kind]
    b.inputs['Roughness'].default_value = rough
    if kind == 'metal':
        b.inputs['Metallic'].default_value = 0.9
    if kind in ('glow', 'screen'):
        b.inputs['Emission Color'].default_value = rgba
        b.inputs['Emission Strength'].default_value = 2.0 if kind == 'glow' else 0.6
    if kind == 'ghost':
        b.inputs['Alpha'].default_value = rgba[3]
        try:
            m.surface_render_method = 'BLENDED'
        except Exception:
            m.blend_method = 'BLEND'
    m.diffuse_color = rgba            # 뷰포트 Solid 모드 색
    return m


for name, shape, rgba, col, kind in items:
    f = os.path.join(tmp, name + '.stl')
    cq.exporters.export(cq.Workplane().add(shape), f, tolerance=0.02, angularTolerance=0.06)
    bpy.ops.wm.stl_import(filepath=f)
    ob = bpy.context.selected_objects[0]
    ob.name = ob.data.name = name
    for c in ob.users_collection:
        c.objects.unlink(ob)
    cols[col].objects.link(ob)
    # 모델 좌표(mm, Y 위, Z 벽→앞) → Blender(m, Z 위, 정면이 -Y)
    ob.scale = (0.001, 0.001, 0.001)
    ob.rotation_euler = (math.radians(90), 0, 0)
    ob.data.materials.append(material(name, rgba, kind))
    bpy.context.view_layer.objects.active = ob
    for o in bpy.context.selected_objects:
        o.select_set(o is ob)
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    try:
        bpy.ops.object.shade_auto_smooth(angle=math.radians(30))
    except Exception:
        bpy.ops.object.shade_smooth()
    if col == K:
        ob.hide_render = True

# 조명·카메라 (F12 로 바로 렌더 가능)
world = bpy.data.worlds.new('World'); sc.world = world
world.use_nodes = True
world.node_tree.nodes['Background'].inputs['Color'].default_value = (0.9, 0.88, 0.84, 1)
world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.8
sun = bpy.data.objects.new('Sun', bpy.data.lights.new('Sun', 'SUN'))
sun.data.energy = 3.0
sun.rotation_euler = (math.radians(50), math.radians(-20), math.radians(-35))
sc.collection.objects.link(sun)
cam = bpy.data.objects.new('Camera', bpy.data.cameras.new('Camera'))
cam.data.lens = 50
cam.location = (0.32, -0.42, 0.22)
sc.collection.objects.link(cam)
tgt = bpy.data.objects.new('CameraTarget', None); tgt.location = (0, 0, 0.105)
sc.collection.objects.link(tgt)
tc = cam.constraints.new('TRACK_TO'); tc.target = tgt; tc.track_axis = 'TRACK_NEGATIVE_Z'; tc.up_axis = 'UP_Y'
sc.camera = cam
sc.render.resolution_x, sc.render.resolution_y = 1600, 1200

bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(f'{OUT}/DataCat_doorbell_RevD.blend'))
bpy.ops.export_scene.gltf(filepath=os.path.abspath(f'{OUT}/DataCat_doorbell_RevD.glb'), export_format='GLB',
                          use_selection=False, export_apply=True)
for o in bpy.data.objects:
    if o.type == 'MESH':
        d = o.dimensions
        print(f'{o.name:26s} {d.x*1000:7.1f} x {d.y*1000:7.1f} x {d.z*1000:7.1f} mm')
