import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.patches import FancyBboxPatch, Circle, Rectangle
import model as M
fp = [f for f in fm.findSystemFonts() if 'NotoSansCJK' in f or 'NotoSansKR' in f]
if fp:
    fm.fontManager.addfont(fp[0]); plt.rcParams['font.family'] = fm.FontProperties(fname=fp[0]).get_name()
fig, ax = plt.subplots(figsize=(8.5, 11), dpi=150)
ax.add_patch(FancyBboxPatch((-M.W/2 + M.R_PLAN, M.R_PLAN), M.W - 2*M.R_PLAN, M.H - 2*M.R_PLAN,
             boxstyle=f"round,pad={M.R_PLAN}", fc='#f4f1ea', ec='#555', lw=1.5))
w = M.WINDOW; ax.add_patch(Rectangle((w['cx']-w['w']/2, w['cy']-w['h']/2), w['w'], w['h'], fc='#222', ec='none'))
ax.add_patch(Rectangle((-M.PI['wid']/2, M.PI_Y0), M.PI['wid'], M.PI['len'], fc='none', ec='#2f7044', lw=1.2, ls='--'))
ax.text(0, M.PI_Y0 - 3, 'Pi 4 외곽 (뒤쪽)', ha='center', va='top', fontsize=8, color='#2f7044')
v = M.VISOR; ax.add_patch(FancyBboxPatch((v['cx']-v['w']/2+v['h']/2, v['cy']-v['h']/2), v['w']-v['h'], v['h'],
             boxstyle=f"round,pad=0,rounding_size={v['h']/2}", fc='#111', ec='none'))
ax.add_patch(Circle((M.BUTTON['cx'], M.BUTTON['cy']), M.BUTTON['hole']/2, fc='#ccc', ec='#666'))
ax.add_patch(Circle((M.SPEAKER['cx'], M.SPEAKER['cy']), M.SPEAKER['dia']/2, fc='none', ec='#666', ls=':'))
a = M.AMP; ax.add_patch(Rectangle((a['cx']-a['w']/2, a['cy']-a['h']/2), a['w'], a['h'], fc='#5b3a9a33', ec='#5b3a9a'))
ax.text(a['cx'], a['cy']-a['h']/2-1.5, 'MAX98357A\n(끼움+폼테이프)', ha='center', va='top', fontsize=7, color='#5b3a9a')
t = M.TOF; ax.add_patch(Rectangle((M.TOF_POS[0]-t['w']/2, M.TOF_POS[1]-t['h']/2), t['w'], t['h'], fc='#b2282e33', ec='#b2282e'))
ax.text(M.TOF_POS[0], M.TOF_POS[1]+t['h']/2+1.5, 'VL53L0X (끼움+폼테이프)', ha='center', va='bottom', fontsize=7, color='#b2282e')
x0, x1, y0, y1, *_ = M.HDMI_KEEP
ax.add_patch(Rectangle((x0, y0), x1-x0, y1-y0, fc='#f2a33a55', ec='#f2a33a'))
ax.text((x0+x1)/2, y1+1, 'HDMI\n케이블', ha='center', va='bottom', fontsize=7, color='#b06d10')
def mark(x, y, c, lab, dx=4, dy=0, ha='left'):
    ax.plot(x, y, 'o', ms=7, mfc=c, mec='k', zorder=5)
    ax.annotate(lab, (x, y), (x+dx, y+dy), fontsize=7.5, ha=ha, va='center', zorder=6)
for x, y in M.FRAME_SCREWS:
    mark(x, y, '#e74c3c', f'M3×10 + 인서트\n({x:+.0f}, {y:.0f})', dx=(5 if x > 0 else -5), ha=('left' if x > 0 else 'right'))
for lx, ly in M.PI['holes']:
    x, y = M.pi_world(lx, ly); mark(x, y, '#3498db', f'M2.5×6\n({x:+.1f}, {y:.0f})', dx=(-4 if x > 0 else 4), ha=('right' if x > 0 else 'left'))
import cadquery as cq
from cadquery import Vector as V
cam_pts = []
for hx, hy in M.cam_holes_local():
    c = M.cam_place(cq.Solid.makeSphere(0.1, V(hx, hy, 0))).Center()
    cam_pts.append((c.x, c.y)); ax.plot(c.x, c.y, 'o', ms=5, mfc='#9b59b6', mec='k', zorder=5)
top = max(cam_pts, key=lambda p: p[1])
ax.annotate('카메라 M2×5 태핑 ×4\n(세로 장착, 아래 20°·왼쪽 15° 보스)', top, (-62, M.H - 6), fontsize=7.5, arrowprops=dict(arrowstyle='-', lw=.6))
for y in M.WALL_SCREW_Y:
    mark(0, y, '#f1c40f', f'벽 ø4×25 접시 + 칼블럭 (0, {y:.0f})', dx=0, dy=-6, ha='center')
ax.add_patch(Circle((0, M.POWER_Y), 8, fc='none', ec='#999', ls='--')); ax.text(0, M.POWER_Y, '전원선\nø16', ha='center', va='center', fontsize=7, color='#777')
mark(6, 0, '#2ecc71', 'M3×16 바닥 잠금 (X +6, 아래→위)', dx=0, dy=-7, ha='center')
for mx, my in M.MIC_HOLES: ax.plot(mx, my, 'o', ms=2.5, color='k')
ax.annotate('마이크 구멍 ø1.6 ×3', M.MIC_HOLES[2], (M.MIC_HOLES[2][0] + 10, M.MIC_HOLES[2][1] + 4), fontsize=7.5, arrowprops=dict(arrowstyle='-', lw=.6))
ax.set_xlim(-75, 75); ax.set_ylim(-15, M.H + 12); ax.set_aspect('equal')
ax.set_title('DataCat Rev E — 나사 위치도 (정면에서 본 좌표, mm)\n원점: 본체 아래 가운데 · X 오른쪽 + · Y 위 +', fontsize=10)
ax.grid(alpha=.25)
fig.tight_layout(); fig.savefig('out/screw_map.png'); print('ok')
