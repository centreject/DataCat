import json, os, shutil
import cadquery as cq
from cadquery import Vector as V
import model as M
import checks

rep, parts, comps = checks.run()
O = 'out/final'
shutil.rmtree(O, ignore_errors=True)
for d in ('step', 'stl_print', 'images'):
    os.makedirs(f'{O}/{d}', exist_ok=True)

# 1) 부품별 STEP (조립 좌표 그대로 — Fusion 에서 바로 맞물림)
for k, v in parts.items():
    cq.exporters.export(cq.Workplane().add(v), f'{O}/step/{k}.step')

# 2) 출력 방향 STL (바닥에 놓을 면을 z=0 으로)
def to_bed(shape, flip):
    s = shape.rotate(V(0, 0, 0), V(1, 0, 0), 180) if flip else shape
    bb = s.BoundingBox()
    return s.translate(V(-(bb.xmin + bb.xmax) / 2, -(bb.ymin + bb.ymax) / 2, -bb.zmin))
orient = {'01_front_shell': True, '02_lcd_pi_chassis': True, '03_wall_plate': False,
          '04_black_visor': True, '05_led_light_pipe': False}
import trimesh
for k, v in parts.items():
    fn = f'{O}/stl_print/{k}_print.stl'
    cq.exporters.export(cq.Workplane().add(to_bed(v, orient[k])), fn, tolerance=0.02, angularTolerance=0.05)
    # 면적 0 인 부스러기 삼각형(테셀레이션 찌꺼기) 제거 → 슬라이서 경고 방지
    m = trimesh.load(fn)
    keep = [c for c in m.split(only_watertight=False) if c.area > 1.0]
    trimesh.util.concatenate(keep).export(fn)

# 3) 전체 조립 STEP (실제 부품 포함, 색 지정)
col = {
    '01_front_shell': (0.93, 0.91, 0.87), '02_lcd_pi_chassis': (0.49, 0.51, 0.54), '03_wall_plate': (0.85, 0.83, 0.78),
    '04_black_visor': (0.06, 0.06, 0.07), '05_led_light_pipe': (1.0, 0.7, 0.3),
}
assy = cq.Assembly(name='DataCat_doorbell_RevE')
for k, v in parts.items():
    assy.add(v, name=k, color=cq.Color(*col[k]))
cc = {'Raspberry Pi 4': (0.18, 0.44, 0.27), '3.5인치 HDMI LCD': (0.1, 0.1, 0.1), 'Camera Module 3 Wide': (0.18, 0.44, 0.27),
      'VL53L0X ToF': (0.7, 0.15, 0.18), 'USB 핀마이크': (0.1, 0.1, 0.1), 'MAX98357A 앰프': (0.3, 0.15, 0.5),
      '스피커 ø28': (0.16, 0.16, 0.17), '16mm 호출벨': (0.8, 0.8, 0.8), '상태 LED': (1, 0.8, 0.5), 'USB-C L형 플러그': (0.1, 0.1, 0.1),
      'HDMI FPC 케이블(공간)': (0.95, 0.64, 0.23), 'GPIO 27~40 배선(공간)': (0.95, 0.64, 0.23), 'ToF 핀헤더·듀폰(공간)': (0.95, 0.64, 0.23),
      'M3x10 (섀시)': (0.75, 0.76, 0.78), 'M3 인서트': (0.79, 0.64, 0.15), 'M2.5x6 태핑 (Pi)': (0.75, 0.76, 0.78),
      'M2x5 태핑 (카메라)': (0.75, 0.76, 0.78), 'M3x16 (바닥 잠금)': (0.75, 0.76, 0.78), 'ø4x25 접시 (벽)': (0.75, 0.76, 0.78)}
ascii_name = {'Raspberry Pi 4': 'REF_raspberry_pi_4', '3.5인치 HDMI LCD': 'REF_waveshare_3p5in_hdmi_lcd',
              'Camera Module 3 Wide': 'REF_camera_module_3_wide_portrait', 'VL53L0X ToF': 'REF_tof_vl53l0x_v2',
              'USB 핀마이크': 'REF_usb_pin_mic', 'MAX98357A 앰프': 'REF_max98357a_amp', '스피커 ø28': 'REF_speaker_driver_28mm',
              '16mm 호출벨': 'REF_button_16mm', '상태 LED': 'REF_status_led', 'USB-C L형 플러그': 'REF_usbc_right_angle_plug',
              'HDMI FPC 케이블(공간)': 'KEEPOUT_hdmi_fpc_cable', 'GPIO 27~40 배선(공간)': 'KEEPOUT_gpio27_40_wiring',
              'ToF 핀헤더·듀폰(공간)': 'KEEPOUT_tof_header_dupont',
              'M3x10 (섀시)': 'HW_M3x10_pan_x4', 'M3 인서트': 'HW_M3_heat_insert_OD4p5_L4_x4', 'M2.5x6 태핑 (Pi)': 'HW_M2p5x6_self_tap_x4',
              'M2x5 태핑 (카메라)': 'HW_M2x5_self_tap_x4', 'M3x16 (바닥 잠금)': 'HW_M3x16_pan_x1', 'ø4x25 접시 (벽)': 'HW_4x25_countersunk_x2'}
for k, v in comps.items():
    if k.startswith('_'):
        continue
    assy.add(v, name=ascii_name[k], color=cq.Color(*cc[k]))
assy.save(f'{O}/step/DataCat_doorbell_RevE_assembly.step')

# 4) 검증 결과
json.dump(rep, open(f'{O}/validation.json', 'w'), ensure_ascii=False, indent=1)
for f in ('hero', 'front', 'side', 'exploded', 'xray', 'back', 'section'):
    shutil.copy(f'out/{f}.png', f'{O}/images/{f}.png')
shutil.copy('model.py', f'{O}/model.py')
shutil.copy('checks.py', f'{O}/checks.py')
import printcheck
pr = {k: printcheck.analyse(v, printcheck.ORIENT[k]) for k, v in parts.items()}
json.dump(pr, open(f'{O}/printcheck.json', 'w'), ensure_ascii=False, indent=1)
shutil.copy('printcheck.py', f'{O}/printcheck.py')
print(json.dumps({k: rep[k] for k in ('interference_mm3', 'fov_blocked_mm3')}, ensure_ascii=False))
for k, v in rep['parts'].items():
    print(k, v['volume_cm3'], 'cm3', v['bbox'])
