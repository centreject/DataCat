"""서보 각도별(10·20·30°) 카메라 위치를 옆에서 본 그림 (out/tilt_range.png)"""
import math, tempfile, os
import numpy as np, trimesh, cadquery as cq
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib import font_manager as fm
import model as M
fp = [f for f in fm.findSystemFonts() if 'NotoSansCJK' in f or 'NotoSansKR' in f]
if fp:
    fm.fontManager.addfont(fp[0]); plt.rcParams['font.family'] = fm.FontProperties(fname=fp[0]).get_name()

def tris(shape):
    with tempfile.TemporaryDirectory() as d:
        f = os.path.join(d, 'a.stl'); cq.exporters.export(cq.Workplane().add(shape), f, tolerance=0.1)
        m = trimesh.load(f)
    return m.triangles[:, :, [2, 1]]          # (z, y)

parts, comps = M.build_all()
sec = parts['01_front_shell'].intersect(M.box(M.CAM_POS[0] - 0.5, M.CAM_POS[0] + 0.5, 120, M.H + 1, -1, M.D + 1))
fig, ax = plt.subplots(figsize=(7, 7), dpi=150)
ax.add_collection(PolyCollection(tris(sec), fc='#d9d3c8', ec='none'))
ax.add_collection(PolyCollection(tris(comps['SG90 서보']), fc='#2f5fc433', ec='none'))
sb = comps['SG90 서보'].BoundingBox(); ax.text((sb.zmin + sb.zmax) / 2, sb.ymax + 1.5, 'SG90 (카메라 오른쪽 뒤)', ha='center', fontsize=7.5, color='#2f5fc4')
cols = {M.CAM['tilt_min']: '#2e86de', M.CAM['tilt']: '#27ae60', M.CAM['tilt_max']: '#c0392b'}
for t, c in cols.items():
    cam = M.tilt_about_pivot(comps['Camera Module 3 Wide'], t)
    cr = M.build_cradle(t)
    ax.add_collection(PolyCollection(tris(cam), fc=c + '55', ec='none'))
    ax.add_collection(PolyCollection(tris(cr), fc=c + '22', ec='none'))
    lc, d = M.lens_center(t), M.cam_dir(t)
    for dv in (-51, 51):     # 세로 화각 가장자리
        a = math.radians(t + dv) if False else None
    # 세로 화각 102° 가장자리 광선 (YZ 평면 투영)
    base = math.atan2(d.y, d.z)
    for k in (-1, 1):
        ang = base + k * math.radians(51)
        ax.plot([lc.z, lc.z + 60 * math.cos(ang)], [lc.y, lc.y + 60 * math.sin(ang)], color=c, lw=0.8, ls='--')
    ax.plot([], [], color=c, label=f'아래 {t:g}°')
py, pz = M.PIVOT
ax.plot(pz, py, 'k+', ms=12); ax.annotate('회전축 (M2 핀 / 서보 축)', (pz, py), (pz - 30, py - 22), fontsize=8, arrowprops=dict(arrowstyle='-', lw=.6))
ax.set_xlim(0, 75); ax.set_ylim(118, M.H + 6); ax.set_aspect('equal')
ax.set_xlabel('벽에서 앞쪽 (mm)'); ax.set_ylabel('높이 (mm)')
ax.set_title(f'Rev F — 서보로 카메라 각도 조절 (옆에서 본 단면, X = {M.CAM_POS[0]:g})\n점선: 각도별 세로 화각 102° 경계', fontsize=10)
ax.legend(loc='lower right', fontsize=8); ax.grid(alpha=.25)
fig.tight_layout(); fig.savefig('out/tilt_range.png'); print('ok')
