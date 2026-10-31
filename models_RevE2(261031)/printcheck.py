"""출력 방향(STL)에서 서포트가 필요한 아랫면(45°보다 눕고 바닥에 닿지 않는 면) 넓이를 잰다."""
import json, math, sys, tempfile, os
import numpy as np, trimesh
import cadquery as cq
from cadquery import Vector as V
import model as M

ORIENT = {'01_front_shell': True, '02_lcd_pi_chassis': True, '03_wall_plate': False,
          '04_black_visor': True, '05_led_light_pipe': False, '06_camera_holder': 'holder'}


def to_bed(shape, flip):
    if flip == 'holder':                     # 카메라 기판 닿는 면이 바닥
        s = M.holder_to_print(shape)
    else:
        s = shape.rotate(V(0, 0, 0), V(1, 0, 0), 180) if flip else shape
    bb = s.BoundingBox()
    return s.translate(V(-(bb.xmin + bb.xmax) / 2, -(bb.ymin + bb.ymax) / 2, -bb.zmin))


def analyse(shape, flip, max_angle=45.0, bridge=6.0):
    s = to_bed(shape, flip)
    with tempfile.TemporaryDirectory() as d:
        f = os.path.join(d, 'p.stl')
        cq.exporters.export(cq.Workplane().add(s), f, tolerance=0.02, angularTolerance=0.05)
        m = trimesh.load(f)
    n, c, a = m.face_normals, m.triangles_center, m.area_faces
    down = n[:, 2] < -math.cos(math.radians(90 - max_angle)) + 1e-6   # 수평에서 45° 보다 누운 아랫면
    off_bed = c[:, 2] > 0.3
    cand = down & off_bed
    # 짧은 다리(브리지) 구분: 아랫면 삼각형 묶음의 가로세로 중 짧은 쪽이 bridge 이하이면 브리지로 본다
    sub = m.submesh([np.where(cand)[0]], append=True) if cand.any() else None
    regions = []
    if sub is not None and len(sub.faces):
        for comp in sub.split(only_watertight=False):
            ext = comp.bounds[1] - comp.bounds[0]
            area = float(comp.area)
            if area < 1.0:
                continue
            kind = 'bridge' if min(ext[0], ext[1]) <= bridge else 'support'
            regions.append({'kind': kind, 'area_mm2': round(area, 1), 'size_xy': [round(ext[0], 1), round(ext[1], 1)],
                            'z': round(float(comp.bounds[0][2]), 1)})
    bb = m.bounds[1] - m.bounds[0]
    return {'bed_size_mm': [round(x, 1) for x in bb], 'support_area_mm2': round(sum(r['area_mm2'] for r in regions if r['kind'] == 'support'), 1),
            'bridge_area_mm2': round(sum(r['area_mm2'] for r in regions if r['kind'] == 'bridge'), 1),
            'regions': sorted(regions, key=lambda r: -r['area_mm2'])[:12]}


if __name__ == '__main__':
    parts, _ = M.build_all()
    rep = {k: analyse(v, ORIENT[k]) for k, v in parts.items()}
    json.dump(rep, open('out/printcheck.json', 'w'), ensure_ascii=False, indent=1)
    for k, r in rep.items():
        print(k, r['bed_size_mm'], 'support', r['support_area_mm2'], 'bridge', r['bridge_area_mm2'])
        for g in r['regions'][:8]:
            print('   ', g)
