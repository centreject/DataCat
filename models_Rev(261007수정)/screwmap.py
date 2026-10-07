import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.patches import FancyBboxPatch, Circle, Rectangle
import model as M
fp = [f for f in fm.findSystemFonts() if 'NotoSansCJK' in f or 'NotoSansKR' in f]
if fp:
    fm.fontManager.addfont(fp[0]); plt.rcParams['font.family'] = fm.FontProperties(fname=fp[0]).get_name()
fig, ax = plt.subplots(figsize=(8.5, 12), dpi=150)
ax.add_patch(FancyBboxPatch((-M.W/2 + M.R_PLAN, M.R_PLAN), M.W - 2*M.R_PLAN, M.H - 2*M.R_PLAN,
             boxstyle=f"round,pad={M.R_PLAN}", fc='#f4f1ea', ec='#555', lw=1.5))
w = M.WINDOW; ax.add_patch(Rectangle((w['cx']-w['w']/2, w['cy']-w['h']/2), w['w'], w['h'], fc='#222', ec='none'))
ax.add_patch(Rectangle((-M.PI['wid']/2, M.PI_Y0), M.PI['wid'], M.PI['len'], fc='none', ec='#2f7044', lw=1.2, ls='--'))
ax.text(0, M.PI_Y0 - 3, 'Pi 4 외곽 (뒤쪽)', ha='center', va='top', fontsize=8, color='#2f7044')
v = M.VISOR; ax.add_patch(FancyBboxPatch((v['cx']-v['w']/2+v['h']/2, v['cy']-v['h']/2), v['w']-v['h'], v['h'],
             boxstyle=f"round,pad=0,rounding_size={v['h']/2}", fc='#111', ec='none'))
ax.add_patch(Circle((M.BUTTON['cx'], M.BUTTON['cy']), M.BUTTON['hole']/2, fc='#ccc', ec='#666'))
ax.add_patch(Circle((M.SPEAKER['cx'], M.SPEAKER['cy']), M.SPEAKER['dia']/2, fc='none', ec='#666', ls=':'))
x0, x1, y0, y1, *_ = M.HDMI_KEEP
ax.add_patch(Rectangle((x0, y0), x1-x0, y1-y0, fc='#f2a33a55', ec='#f2a33a'))
ax.text((x0+x1)/2, y1+1, 'HDMI\n케이블', ha='center', va='bottom', fontsize=7, color='#b06d10')
def mark(x, y, c, lab, dx=4, dy=0, ha='left'):
    ax.plot(x, y, 'o', ms=7, mfc=c, mec='k', zorder=5)
    ax.annotate(lab, (x, y), (x+dx, y+dy), fontsize=7.5, ha=ha, va='center', zorder=6)
for x, y in M.FRAME_SCREWS:
    mark(x, y, '#e74c3c', f'M3 인서트\n({x:+.0f}, {y:.0f})', dx=(5 if x > 0 else -5), ha=('left' if x > 0 else 'right'))
for lx, ly in M.PI['holes']:
    x, y = M.pi_world(lx, ly); mark(x, y, '#3498db', f'M2.5\n({x:+.1f}, {y:.0f})', dx=(-4 if x > 0 else 4), ha=('right' if x > 0 else 'left'))
for (x, y) in [(-30.5, 186.5), (-30.5, 174.2), (-9.5, 186.5), (-9.5, 174.2)]:
    ax.plot(x, y, 'o', ms=5, mfc='#9b59b6', mec='k', zorder=5)
ax.annotate('카메라 M2×5 ×4\n(10° 기울어진 보스)', (-30.5, 186.5), (-50, 205), fontsize=7.5, arrowprops=dict(arrowstyle='-', lw=.6))
for y in (70.0, 165.0):
    mark(0, y, '#f1c40f', f'벽 나사 ø4 접시 (0, {y:.0f})', dx=0, dy=-6, ha='center')
ax.add_patch(Circle((0, 118), 8, fc='none', ec='#999', ls='--')); ax.text(0, 118, '전원선\nø16', ha='center', va='center', fontsize=7, color='#777')
mark(6, 0, '#2ecc71', 'M3×20 바닥 잠금 (X +6, 아래→위)', dx=0, dy=-7, ha='center')
for mx, my in M.MIC_HOLES: ax.plot(mx, my, 'o', ms=2.5, color='k')
ax.annotate('마이크 구멍 ø1.4 ×3', (19, 156), (35, 160), fontsize=7.5, arrowprops=dict(arrowstyle='-', lw=.6))
ax.set_xlim(-75, 75); ax.set_ylim(-15, 225); ax.set_aspect('equal')
ax.set_title('DataCat Rev D — 나사 위치도 (정면에서 본 좌표, mm)\n원점: 본체 아래 가운데 · X 오른쪽 + · Y 위 +', fontsize=10)
ax.grid(alpha=.25)
fig.tight_layout(); fig.savefig('out/screw_map.png'); print('ok')
