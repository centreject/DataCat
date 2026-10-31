"""
DataCat 무인현관 초인종 외함 — Rev E.2 (고정형) · 2026-10-31 구매 부품 반영
  - 스피커: 70 x 31 x 16.5 상자형 4Ω 3W (나사 구멍 63.6 x 24, ø3) → 버튼 오른쪽, M2.5 x 6 태핑 4개
  - 소리: USB 사운드카드 스틱(66 x 18) → Pi USB 2.0 아래 포트. MAX98357A 앰프 삭제
  - 거리 센서: VL53L5CX V2 보드(24.1 x 10), 화각 45° x 45°
  - 가로 105 → 124 mm (스피커와 버튼을 나란히 두려고). 세로 192 그대로
  - USB 핀마이크 → USB 3.0 위 포트, 사운드카드 스틱 → USB 2.0 아래 포트 (서로 다른 줄이라 안 겹침)
  - ToF 핀은 일자 핀헤더 대신 선을 직접 납땜 (또는 ㄱ자 헤더) — 뒤로 공간이 없음

이전 판: Rev E

Rev E 변경 (2026-10-28 하드웨어 구성 기준) · Rev E.1: 세로 215 → 192 mm (바이저를 Pi USB 포트 앞쪽으로 내리고 아래 줄을 올림)
  - 거리 센서: VL53L5CX(Qwiic Mini) → VL53L0X V2 보드(25 x 10.7), 화각 25°
  - 카메라: Camera Module 3 Wide 를 세로로(90° 회전) 달고 아래로 20°, 문 쪽(정면에서 왼쪽)으로 15° 돌림
            → 세로 화각 102° 로 방문객 얼굴과 문 앞 바닥을 한 장에 담는다
  - 스피커: USB 스피커 삭제 → MAX98357A I2S 앰프 + ø28 스피커. 앰프는 버튼 왼쪽 홈에 끼움
  - 마이크: USB 핀마이크(JMTek) — Rev D 와 같은 USB2 위쪽 포트
  - 3D 출력: 서포트 없이 뽑히도록 스피커 선반 삭제, 벽 브래킷 갈고리 밑 45° 모따기,
            인서트·나사 구멍을 실제 나사 규격에 맞춤(아래 FASTENERS), 작은 구멍 최소 ø1.6
  - LCD(Waveshare 3.5" HDMI), 16 mm 호출벨, 외형은 Rev D 그대로

좌표계 (단위 mm)
  X : 정면에서 봤을 때 오른쪽 +
  Y : 위 +  (바닥 0, 꼭대기 H)
  Z : 벽에서 바깥쪽 +  (벽면 0, 전면 D)

실제 부품 치수로 내부를 먼저 배치하고, 외형은 레퍼런스 이미지 비율
(가로:세로 ≈ 1:2, 큰 라운드 알약형, 상단 블랙 바이저, 하단 화면+버튼+그릴)을 따른다.
"""
from __future__ import annotations

import math
import cadquery as cq
from cadquery import Vector as V

# ──────────────────────────────────────────────────────────────
# 외형 파라미터
# ──────────────────────────────────────────────────────────────
W, H, D = 124.0, 192.0, 42.0      # 가로, 세로, 깊이 (Rev E.2/F.2: 가로 105 → 124, 상자형 스피커)
R_PLAN = 40.0                     # 정면에서 본 모서리 반경 (알약형)
T = 2.5                           # 쉘 두께
F_FRONT = 14.0                    # 전면 테두리 라운드 (레퍼런스처럼 둥글게)
F_BACK = 1.5                      # 벽쪽 테두리 라운드
Z_IN = D - T                      # 전면 안쪽 면 z = 39.5

# 전면 요소 위치
VISOR = dict(cx=0.0, cy=161.0, w=72.0, h=24.0, depth=1.2)
PANEL = dict(cx=0.0, cy=77.0, w=96.0, h=130.0, r=16.0, groove=1.2, gdepth=0.8)
WINDOW = dict(cx=0.0, cy=90.0, w=49.5, h=74.0, r=2.0, chamfer=1.2)
LED_SLOT = dict(cx=0.0, cy=137.0, w=16.0, h=2.0)
BUTTON = dict(cx=-33.6, cy=30.0, hole=16.4)
# 상자형 스피커 4Ω 3W: 앞판 69.9 x 31, 깊이 16.5, 나사 구멍 63.6 x 24 (ø3), 아래쪽에 선 나오는 턱 11 mm
SPEAKER = dict(cx=10.0, cy=27.4, L=69.9, h=31.0, depth=16.5, hole_sx=63.6, hole_sy=24.0, hole_d=3.0, setback=6.5,
               flange=2.0, body_L=57.0)
GRILLE = dict(cx=10.0, cy=27.4, cols=9, rows=5, pitch=3.8, hole=1.8)

# ──────────────────────────────────────────────────────────────
# 실제 부품 치수 (데이터시트 기준, 실측 후 조정)
# ──────────────────────────────────────────────────────────────
# Raspberry Pi 4 Model B : PCB 85 x 56 x 1.4, 구멍 M2.5 58 x 49 간격
PI = dict(len=85.0, wid=56.0, pcb=1.4, hole_d=2.7,
          holes=[(3.5, 3.5), (61.5, 3.5), (3.5, 52.5), (61.5, 52.5)])
# Waveshare 3.5inch HDMI LCD (480x320, Pi와 같은 85 x 56 외곽, 26핀 암 헤더로 5V 전원)
# HDMI 리셉터클은 LCD 뒷면 오른쪽 가장자리(Pi micro-HDMI0 바로 위). 도착 후 실측 필요.
LCD = dict(pcb_w=56.0, pcb_h=85.5, pcb_t=1.6, glass_w=54.0, glass_h=77.0, glass_t=4.4,
           act_w=48.96, act_h=73.44, back_t=2.0, hdr_len=33.0, hdr_from_end=7.1, hdr_h=8.5,
           hdmi_w=15.0, hdmi_d=11.5, hdmi_t=6.0)
# Camera Module 3 Wide : 25 x 24, 높이 12.4, 구멍 ø2.2 (21 x 12.5), 렌즈 중심 위 가장자리에서 9.6
# Rev E: 세로로 달기(roll 90°) → 세로 화각 102°, 가로 67°.
#   tilt: 아래로 숙이는 각도, yaw: 문 쪽으로 돌리는 각도(음수 = 정면에서 볼 때 왼쪽).
#   문이 초인종 오른쪽에 있는 집이면 yaw 를 +15 로 바꾸면 된다.
CAM = dict(w=25.0, h=24.0, pcb=1.0, height=12.4, lens_from_top=9.6,
           hole_dx=10.5, hole_rows=(2.0, 14.5), lens_glass=5.75, barrel=8.6,
           fov_half=62.0, tilt=20.0, yaw=-15.0, roll=90.0)
# VL53L0X V2 보드 (GY-VL53L0XV2 / VL53LXX-V2) : 25 x 10.7 x 1.6, 센서 칩 4.4 x 2.4 x 1.0 (가운데)
#   6핀(VIN GND SCL SDA GPIO1 XSHUT) 은 아래쪽 긴 변. 핀헤더를 일자로 납땜했으면 뒤로 듀폰 공간이 필요하다.
#   화각 25° (fov_half 는 창을 낼 때 쓰는 여유 포함 값)
# Rev E.2: VL53L5CX V2 보드 24.1 x 10, 센서 6.4 x 3.0 x 1.75, 화각 45° x 45° (대각 63°)
TOF = dict(w=24.1, h=10.0, pcb=1.6, sens_w=6.4, sens_h=3.0, sens_t=1.75, fov_half=25.0,
           hdr_len=15.3, hdr_back=20.0)
# USB 미니 마이크 동글 (무지향, 예: Adafruit #3367 류) : 22.5 x 18.3 x 7.7, 포트 밖으로 ~10.5 돌출
UMIC = dict(len=10.5, w=18.3, t=7.7)
# MAX98357A I2S 앰프 보드 (Adafruit #3006 형) : 19.1 x 17.8 x 1.6, 스피커 단자대 7.6 x 7.0 x 8.5
#   버튼 왼쪽 아래 홈에 부품면이 뒤로 가게 끼운다. 배선: VIN→5V, GND, BCLK→GPIO18(12번 핀, Pi 뒷면 납땜),
#   LRC→GPIO19(35번 핀), DIN→GPIO21(40번 핀). 스피커는 4~8 Ω 2~3 W, ø28
# USB 사운드카드 스틱 (66 x 18, 두께는 8 로 가정) → Pi USB 3.0 아래 포트. 플러그 12 mm 가 포트 안, 54 mm 가 밖
USB_SND = dict(w=17.6, t=8.0, len=66.0)    # 66 x 18 x 8(두께 가정), USB 플러그 포함 길이
SND_Y0, SND_Z = 54.0, 13.5                  # 스틱 아래 끝 y, 깊이 방향 가운데 z (옆벽에 세움)
# 16 mm 메탈 푸시버튼 + LED 링 : 패널 구멍 ø16, 헤드 ø18, 너트 22 mm, 패널 뒤 길이 ~32
BTN = dict(head=18.0, head_t=2.0, body=16.0, nut=24.0, nut_t=4.0, length=32.0)

# 부품 배치 (월드 좌표)
VIS_Y = VISOR["cy"]
CAM_POS = (-20.0, VIS_Y)          # 렌즈 중심
TOF_POS = (20.0, VIS_Y)           # 센서 중심
OPEN_X1 = -9.0                   # 카메라 쪽 쉘 창 오른쪽 끝 x
HOLDER_HALF = 16.0               # 카메라 홀더 크기 (렌즈 중심에서 ±, 카메라 좌표)
CAM_BLOCK = 9.6                  # 렌즈 받침(9 x 9 사각) 자리 + 틈
MIC_HOLES = [(1.0 + dx, 145.0) for dx in (-3.0, 0.0, 3.0)]   # USB 핀마이크 앞 소리 구멍 (ø1.6)

# ──────────────────────────────────────────────────────────────
# 나사·인서트 (실제 규격). 구멍 치수는 FDM(0.4 노즐, PETG/PLA) 기준
# ──────────────────────────────────────────────────────────────
FASTENERS = dict(
    # 섀시 → 쉘: M3 x 10 냄비머리 + M3 황동 열압입 인서트(외경 4.5, 길이 4)
    m3_insert=dict(hole=4.0, depth=5.5, od=4.5, length=4.0, boss=8.0),
    m3_clear=3.4, m3_head=(5.5, 2.0),
    # Pi → 섀시: M2.5 x 6 태핑(셀프태핑) 냄비머리, 구멍 ø2.2
    m25_pilot=2.2, m25_head=(4.5, 1.8),
    # 카메라 → 쉘: M2 x 5 태핑 냄비머리, 구멍 ø1.8
    m2_pilot=1.8, m2_head=(3.8, 1.4),
    # 바닥 잠금: M3 x 16 냄비머리 기계나사, 브래킷 보스에 ø2.5 로 직접 나사산을 냄
    m3_pilot=2.5,
    # 벽: ø4 x 25 접시머리 나사 + 6 mm 칼블럭(앵커)
    wall_hole=4.6, wall_csk=9.4,
)

# 화면 / Pi 적층 (앞 → 뒤)
LCD_FRONT = Z_IN                                  # 유리 앞면이 쉘 안쪽 면에 닿음
LCD_PCB_FRONT = LCD_FRONT - LCD["glass_t"]        # 35.1
LCD_PCB_BACK = LCD_PCB_FRONT - LCD["pcb_t"]       # 33.5
FRAME_FRONT, FRAME_BACK = LCD_PCB_BACK, LCD_PCB_BACK - 5.0     # 33.5 .. 28.5
BAR_FRONT = FRAME_BACK + 2.0                      # 가로바는 LCD 뒷면 부품(2 mm)을 피해 얇게
# LCD 는 2×13 GPIO 스태킹 헤더(롱핀 11 mm)로 Pi 위에 꽂는다.
# LCD PCB 뒷면 ~ Pi PCB 윗면 = 2.5(Pi 핀 받침) + 8.5(스태킹 헤더) + 8.5(LCD 헤더) = 19.5 mm
# → USB/LAN(높이 16 mm)이 LCD 아래로 들어가고, 27~40번 핀 위로 11 mm 공간이 남는다.
# 실물 조립 후 이 값을 재서 고친다 (모든 z 값이 여기서 따라온다).
STACK = 19.5
PI_TOP = LCD_PCB_BACK - STACK                     # Pi 부품면(앞쪽) z = 14.0
PI_BOTTOM = PI_TOP - PI["pcb"]                    # 12.6
PI_Y0 = WINDOW["cy"] - PI["len"] / 2              # Pi 세로 배치, USB/LAN 위쪽
SPK_FACE = Z_IN - SPEAKER["setback"]              # 스피커 앞판 z (앞벽에서 6.5 뒤: 앞 테두리 곡면을 피함)

# 벽 브래킷
PLATE_T = 3.0
CLEAR = 0.4
SLIDE = 7.4                       # 걸고 내려 끼우는 이동량
# Rev D.1: 벽 브래킷 아래쪽(Y < PLATE_SKIRT)은 쉘 바깥 윤곽까지 넓혀 뒷면 아래 틈을 막는다.
# 그만큼 쉘 뒤 테두리를 아래쪽에서 PLATE_T + CLEAR 깊이로 따내서, 쉘을 올린 채 벽에 대도 걸리지 않는다.
PLATE_SKIRT = 40.0
WALL_SCREW_Y = (60.0, 142.0)       # 벽 고정 나사 위치 (X 0)
POWER_Y = 114.0                   # 벽 타공 전원선 구멍 ø16


# ──────────────────────────────────────────────────────────────
# 도형 헬퍼
# ──────────────────────────────────────────────────────────────
def box(x0, x1, y0, y1, z0, z1) -> cq.Shape:
    return cq.Solid.makeBox(x1 - x0, y1 - y0, z1 - z0, V(x0, y0, z0))


def cyl(r, z0, z1, x, y) -> cq.Shape:
    return cq.Solid.makeCylinder(r, z1 - z0, V(x, y, z0), V(0, 0, 1))


def rrect(w, h, r, z0, z1, cx=0.0, cy=0.0) -> cq.Workplane:
    r = min(r, min(w, h) / 2 - 0.01)
    return (cq.Workplane("XY", origin=(cx, cy, z0))
            .sketch().rect(w, h).vertices().fillet(r).finalize()
            .extrude(z1 - z0))


def pill(w, h, z0, z1, cx, cy) -> cq.Shape:
    r = h / 2
    s = box(cx - w / 2 + r, cx + w / 2 - r, cy - r, cy + r, z0, z1)
    s = s.fuse(cyl(r, z0, z1, cx - w / 2 + r, cy)).fuse(cyl(r, z0, z1, cx + w / 2 - r, cy))
    return s.clean()


def frustum(w0, h0, r0, z0, w1, h1, r1, z1, cx, cy) -> cq.Shape:
    s0 = cq.Sketch().rect(w0, h0).vertices().fillet(min(r0, min(w0, h0) / 2 - 0.01))
    s1 = (cq.Sketch().rect(w1, h1).vertices().fillet(min(r1, min(w1, h1) / 2 - 0.01))
          .moved(cq.Location(V(0, 0, z1 - z0))))
    return cq.Workplane("XY", origin=(cx, cy, z0)).placeSketch(s0, s1).loft().val()


def plan(off=0.0) -> tuple[float, float, float]:
    """정면 외곽을 off 만큼 안/밖으로 옮긴 (w, h, r)"""
    return W + 2 * off, H + 2 * off, R_PLAN + off


# ──────────────────────────────────────────────────────────────
# 카메라 좌표계 (아래로 tilt 만큼 숙임)
# ──────────────────────────────────────────────────────────────
# 렌즈 앞면 중심 z: 렌즈가 기울어져도 렌즈통 앞 테두리가 앞면보다 0.3 안쪽에 있도록 뒤로 뺀다
_AX = math.acos(math.cos(math.radians(CAM["tilt"])) * math.cos(math.radians(CAM["yaw"])))
LENS_FRONT_Z = D - 0.3 - CAM["barrel"] / 2 * math.sin(_AX)


def cam_place(shape: cq.Shape) -> cq.Shape:
    """카메라 로컬(렌즈 중심 원점, 기판 앞면 z=0, 시선 +z) → 월드.
    순서: 렌즈 축으로 roll(세로 장착) → 아래로 tilt → 문 쪽으로 yaw"""
    lens_h = CAM["height"] - CAM["pcb"]           # 기판 앞면에서 렌즈 앞까지 11.4
    s = shape.rotate(V(0, 0, 0), V(0, 0, 1), CAM["roll"])
    s = s.translate(V(0, 0, -lens_h))             # 렌즈 앞면 중심을 원점으로
    s = s.rotate(V(0, 0, 0), V(1, 0, 0), CAM["tilt"])   # +X축 회전 → 시선이 아래로
    s = s.rotate(V(0, 0, 0), V(0, 1, 0), CAM["yaw"])    # +Y축 회전 → 시선이 +X 쪽으로
    return s.translate(V(CAM_POS[0], CAM_POS[1], LENS_FRONT_Z))


def cam_dir() -> V:
    a, b = math.radians(CAM["tilt"]), math.radians(CAM["yaw"])
    return V(math.cos(a) * math.sin(b), -math.sin(a), math.cos(a) * math.cos(b))


def cam_holes_local():
    top = CAM["lens_from_top"]
    return [(sx * CAM["hole_dx"], top - row) for sx in (-1, 1) for row in CAM["hole_rows"]]


def lens_cut() -> cq.Shape:
    """렌즈 구멍: 기울어진 축을 따라 렌즈통 원통 + 센서 화각 사각뿔(102° x 67° 에 여유 4~6°).
    원뿔로 파면 기울어진 쪽 구멍이 너무 길어져서, 실제 화각 모양 그대로 판다. 쉘과 바이저에 같이 쓴다"""
    d = cam_dir()
    lens_c = V(CAM_POS[0], CAM_POS[1], LENS_FRONT_Z)
    barrel_r = CAM["barrel"] / 2 + 0.5
    cut = cq.Solid.makeCylinder(barrel_r, 14, lens_c - d * 12, d)
    lens_h = CAM["height"] - CAM["pcb"]
    g0, L = CAM["lens_glass"] + 1.0, 18.0
    gw, gh = L * math.tan(math.radians(55)), L * math.tan(math.radians(38))   # 로컬 x = 센서 긴 변
    fov = cam_place(frustum(g0, g0, 0.01, lens_h - 0.3, g0 + 2 * gw, g0 + 2 * gh, 0.01, lens_h + L, 0, 0))
    # 화각 가장자리(벽에 붙은 바닥 쪽)는 앞면과 거의 나란히 나가서 구멍이 길어진다.
    # 블랙 바이저 안(가장자리 2 mm 남김)으로만 파서 흰 쉘에는 구멍이 생기지 않게 한다.
    v = VISOR
    keep = pill(v["w"] - 4.0, v["h"] - 4.0, Z_IN - 12.0, D + 1, v["cx"], v["cy"])
    cut = cut.fuse(fov.intersect(keep))
    return cut.clean()


def cam_opening(z0, z1) -> cq.Shape:
    """카메라 쪽 쉘 창: 바이저 안쪽(가장자리 1.5 mm 남김, 렌즈 구멍보다 0.5 mm 넓게) 중 x <= OPEN_X1 부분. 바이저가 창 테두리를 덮는다"""
    v = VISOR
    return pill(v["w"] - 3.0, v["h"] - 3.0, z0, z1, v["cx"], v["cy"]).intersect(box(-60, OPEN_X1, 0, H, z0 - 1, z1 + 1))


def cam_fov_clear() -> cq.Shape:
    """홀더에서 파낼 화각 (실제 102° x 67° + 여유 2°), 렌즈 앞면부터 바깥으로"""
    lens_h = CAM["height"] - CAM["pcb"]
    g0, L = CAM["lens_glass"] + 0.6, 20.0
    gw, gh = L * math.tan(math.radians(53)), L * math.tan(math.radians(36))
    return cam_place(frustum(g0, g0, 0.01, lens_h - 0.2, g0 + 2 * gw, g0 + 2 * gh, 0.01, lens_h + L, 0, 0))


def build_cam_holder() -> cq.Shape:
    """06 카메라 홀더 (검정 출력): 카메라 기판 앞면 ~ 앞벽 사이를 검게 채우고, 앞부분은 쉘 창에 끼워
    바이저 바로 밑까지 올라온다. 카메라는 M2 x 5 태핑 4개로 홀더에 고정, 홀더는 쉘에 순간접착제.
    출력: 기판 닿는 면이 베드 (렌즈 축이 위로)"""
    lens_h = CAM["height"] - CAM["pcb"]
    blk = cam_place(box(-HOLDER_HALF, HOLDER_HALF, -HOLDER_HALF, HOLDER_HALF, 0.0, lens_h + 12.0))
    blk = blk.intersect(box(-60, OPEN_X1 + 3.0, 0, H, 0, Z_IN))
    plug = cam_opening(Z_IN - 0.5, D - VISOR["depth"] - 0.05).intersect(
        cam_place(box(-40, 40, -40, 40, 0.0, 60)))                          # 창에 끼는 부분 (기판 면 앞쪽만)
    h = blk.fuse(plug)
    h = h.cut(cam_fov_clear())
    h = h.cut(cq.Solid.makeCylinder(CAM["barrel"] / 2 + 0.4, 30, cam_place_pt(0, 0, -1.0), cam_dir()))
    h = h.cut(cam_place(box(-CAM_BLOCK / 2, CAM_BLOCK / 2, -CAM_BLOCK / 2, CAM_BLOCK / 2, -1, 5.6)))  # 렌즈 받침 자리
    h = h.cut(cam_place(cq.Solid.makeCone(CAM_BLOCK * 0.71, 0.0, CAM_BLOCK * 0.71 * 1.25, V(0, 0, 5.59), V(0, 0, 1))))  # 천장 51° 원뿔 (서포트 없이)
    for hx, hy in cam_holes_local():
        h = h.cut(cam_place(cq.Solid.makeCylinder(FASTENERS["m2_pilot"] / 2, 5.5, V(hx, hy, -0.1), V(0, 0, 1))))
    w, hh, r = plan(-T)
    inner = rrect(w, hh, r, -1, Z_IN, cy=H / 2).edges(">Z").fillet(F_FRONT - T).val()
    h = h.intersect(inner.fuse(cam_opening(Z_IN - 1.0, D)))
    return h.clean()


def cam_place_pt(x, y, z) -> V:
    v = cam_place(cq.Vertex.makeVertex(x, y, z))
    return v.Center()


def holder_to_print(shape: cq.Shape) -> cq.Shape:
    """월드 → 카메라 로컬(기판 앞면 z=0, 렌즈 축 +z): 기판 닿는 면이 베드"""
    lens_h = CAM["height"] - CAM["pcb"]
    s = shape.translate(V(-CAM_POS[0], -CAM_POS[1], -LENS_FRONT_Z))
    s = s.rotate(V(0, 0, 0), V(0, 1, 0), -CAM["yaw"])
    s = s.rotate(V(0, 0, 0), V(1, 0, 0), -CAM["tilt"])
    return s.translate(V(0, 0, lens_h))


# ──────────────────────────────────────────────────────────────
# 01 전면 쉘
# ──────────────────────────────────────────────────────────────
def build_shell() -> cq.Shape:
    w, h, r = plan()
    outer = rrect(w, h, r, 0, D, cy=H / 2).edges(">Z").fillet(F_FRONT).edges("<Z").fillet(F_BACK)
    wi, hi, ri = plan(-T)
    inner = rrect(wi, hi, ri, -1, Z_IN, cy=H / 2).edges(">Z").fillet(F_FRONT - T)
    outer_s = outer.val()
    shell = outer_s.cut(inner.val())

    # ── 벽쪽 장식 라인 (레퍼런스의 뒷판 이음선) ──
    w2, h2, r2 = plan(-0.6)
    band = rrect(w + 2, h + 2, r + 1, 5.5, 6.5, cy=H / 2).val().cut(rrect(w2, h2, r2, 5.4, 6.6, cy=H / 2).val())
    shell = shell.cut(band)

    # ── 컨트롤 패널 둘레 홈 ──
    p = PANEL
    ring = rrect(p["w"] + p["groove"], p["h"] + p["groove"], p["r"] + p["groove"] / 2,
                 D - p["gdepth"], D + 1, p["cx"], p["cy"]).val().cut(
        rrect(p["w"] - p["groove"], p["h"] - p["groove"], p["r"] - p["groove"] / 2,
              D - p["gdepth"] - 1, D + 2, p["cx"], p["cy"]).val())
    shell = shell.cut(ring)

    # ── 바이저 자리 (블랙 인서트가 들어가는 1.2 mm 홈) ──
    v = VISOR
    shell = shell.cut(pill(v["w"], v["h"], D - v["depth"], D + 1, v["cx"], v["cy"]))

    # ── 화면 창 + 앞쪽 모따기 ──
    wd = WINDOW
    shell = shell.cut(rrect(wd["w"], wd["h"], wd["r"], Z_IN - 1, D + 1, wd["cx"], wd["cy"]).val())
    c = wd["chamfer"]
    shell = shell.cut(frustum(wd["w"], wd["h"], wd["r"], D - c,
                              wd["w"] + 2 * c + 0.4, wd["h"] + 2 * c + 0.4, wd["r"] + c, D + 0.2,
                              wd["cx"], wd["cy"]))

    # ── 상태 LED 슬롯 ──
    ls = LED_SLOT
    shell = shell.cut(pill(ls["w"], ls["h"], Z_IN - 1, D + 1, ls["cx"], ls["cy"]))

    # ── 호출벨 구멍 (16 mm 버튼, PETG 수축 감안 ø16.4) ──
    shell = shell.cut(cyl(BUTTON["hole"] / 2, Z_IN - 1, D + 1, BUTTON["cx"], BUTTON["cy"]))
    shell = shell.cut(cyl(BTN["nut"] / 2 + 0.4, Z_IN - 1.5, Z_IN, BUTTON["cx"], BUTTON["cy"]))  # 너트 자리 평면 (안쪽 곡면 정리)

    # ── 스피커 그릴 ──
    g = GRILLE
    for i in range(g["cols"]):
        for j in range(g["rows"]):
            x = g["cx"] + (i - (g["cols"] - 1) / 2) * g["pitch"]
            y = g["cy"] + (j - (g["rows"] - 1) / 2) * g["pitch"]
            shell = shell.cut(cyl(g["hole"] / 2, Z_IN - 1, D + 1, x, y))

    # ── 카메라 렌즈 구멍 (기울어진 축을 따라 원통 + 화각 원뿔) ──
    shell = shell.cut(lens_cut())
    shell = shell.cut(cam_opening(Z_IN - 1.0, D + 1.0))   # 홀더 앞부분이 끼는 창 (바이저가 테두리를 덮음)

    # ── ToF 창 (화각 30°로 벌어지는 사각 창) ──
    tx, ty = TOF_POS
    sens_front = Z_IN - 0.2
    grow = (D - sens_front + 0.5) * math.tan(math.radians(TOF["fov_half"]))
    shell = shell.cut(frustum(TOF["sens_w"] + 1.0, TOF["sens_h"] + 1.0, 0.6, sens_front,
                              TOF["sens_w"] + 1.0 + 2 * grow, TOF["sens_h"] + 1.0 + 2 * grow, 1.5, D + 0.5,
                              tx, ty))

    # ── USB 핀마이크 소리 구멍 3개 (FDM 최소 ø1.6) ──
    for mx, my in MIC_HOLES:
        shell = shell.cut(cyl(0.8, Z_IN - 1, D + 1, mx, my))

    # ── 측면 통풍구 (Pi 높이, 양쪽 아래·위 그룹) ──
    # Rev E.2/F.2: 오른쪽 옆벽은 USB 사운드카드 스틱이 붙어서 막힘 → 왼쪽만 두고, 대신 바닥에 슬롯 5개(아래로 들어와 왼쪽으로 빠짐)
    for k in range(5):
        bslot = pill(16, 2.2, -5, 5, 0, 0).rotate(V(0, 0, 0), V(0, 0, 1), 90).rotate(V(0, 0, 0), V(1, 0, 0), 90)
        shell = shell.cut(bslot.translate(V(-18.0 + k * 4.5, T / 2, 19.0)))
    for side in (-1,):
        for y0 in (62.0, 104.0):
            for k in range(6):
                y = y0 + k * 4.5
                # XY 평면의 알약을 Y축으로 90° 돌리면 길이 방향이 Z, 두께 방향이 X 가 된다
                slot = pill(16, 2.2, -5, 5, 0, 0).rotate(V(0, 0, 0), V(0, 1, 0), 90)
                shell = shell.cut(slot.translate(V(side * (W / 2 - T / 2), y, 19.0)))

    # ── 바닥: 케이블 홈(벽쪽) + 잠금 나사 구멍 (M3 통과 ø3.4, 머리 자리 ø6.2 x 1.2) ──
    shell = shell.cut(box(12, 24, -1, 4, -1, 5))
    shell = shell.cut(cq.Solid.makeCylinder(FASTENERS["m3_clear"] / 2, 6, V(6, -1, 7), V(0, 1, 0)))
    shell = shell.cut(cq.Solid.makeCylinder(3.1, 1.4, V(6, -0.1, 7), V(0, 1, 0)))

    # ──────────────── 내부 구조 (안쪽 면에 붙는 것들) ────────────────
    adds: list[cq.Shape] = []

    # LCD 위치 잡이: PCB 네 모서리 L 리브
    lw, lh = LCD["pcb_w"] + 0.4, LCD["pcb_h"] + 0.4
    for sx in (-1, 1):
        for sy in (-1, 1):
            cx, cy = WINDOW["cx"] + sx * lw / 2, WINDOW["cy"] + sy * lh / 2
            leg = 8.0
            # 세로 다리 (모서리 사각형까지 포함해 가로 다리와 겹치게 → 비다양체 모서리 방지)
            adds.append(box(min(cx, cx + sx * 1.5), max(cx, cx + sx * 1.5),
                            min(cy + sy * 1.5, cy - sy * leg), max(cy + sy * 1.5, cy - sy * leg),
                            LCD_PCB_BACK + 0.1, Z_IN + 0.5))
            adds.append(box(min(cx, cx - sx * leg), max(cx, cx - sx * leg),
                            min(cy, cy + sy * 1.5), max(cy, cy + sy * 1.5), LCD_PCB_BACK + 0.1, Z_IN + 0.5))

    # 섀시 고정 보스: M3 열압입 인서트(외경 4.5, 길이 4) → 구멍 ø4.0 x 깊이 5.5, 입구 0.5 모따기
    ins = FASTENERS["m3_insert"]
    for x, y in FRAME_SCREWS:
        b = cyl(ins["boss"] / 2, FRAME_FRONT, Z_IN + 0.5, x, y)
        b = b.cut(cyl(ins["hole"] / 2, FRAME_FRONT - 0.1, FRAME_FRONT + ins["depth"], x, y))
        b = b.cut(cq.Solid.makeCone(ins["hole"] / 2 + 0.6, ins["hole"] / 2, 0.6, V(x, y, FRAME_FRONT - 0.1), V(0, 0, 1)))
        adds.append(b)

    # Rev E.2: 카메라 보스는 쉘에서 빼고 검은 카메라 홀더(06)로 옮김 → 렌즈 구멍으로 흰 보스·기판이 안 보이게

    # ToF 끼움 홈 (보드 25 x 10.7 + 틈 0.3): 좌우 끝 ㄷ자 리브. 보드를 앞으로 밀어 넣고 양면 폼테이프로 고정
    tw, th = TOF["w"] + 0.3, TOF["h"] + 0.3
    tof_board_front = Z_IN - 0.2 - TOF["sens_t"]
    for sx in (-1, 1):
        ex = tx + sx * tw / 2
        adds.append(box(min(ex, ex + sx * 1.6), max(ex, ex + sx * 1.6), ty - th / 2 - 1.6, ty + th / 2 + 1.6,
                        tof_board_front - TOF["pcb"] - 1.0, Z_IN + 0.5))
        for sy in (-1, 1):
            ey = ty + sy * th / 2
            adds.append(box(min(ex, ex - sx * 5.0), max(ex, ex - sx * 5.0), min(ey, ey + sy * 1.6), max(ey, ey + sy * 1.6),
                            tof_board_front - TOF["pcb"] - 1.0, Z_IN + 0.5))

    # 상자형 스피커: 앞판 나사 구멍 4개에 맞춘 보스(앞벽 → 스피커 앞판, ø2.2 구멍에 M2.5 x 6 태핑)
    #   스피커 앞판과 앞벽 사이 4.5 mm 는 소리 통로 — 둘레를 막는 테두리를 둘러 소리가 안쪽으로 새지 않게 한다
    sp = SPEAKER
    for sx in (-1, 1):
        for sy in (-1, 1):
            hx, hy = sp["cx"] + sx * sp["hole_sx"] / 2, sp["cy"] + sy * sp["hole_sy"] / 2
            boss = cyl(2.75, SPK_FACE, Z_IN + 0.5, hx, hy).cut(cyl(FASTENERS["m25_pilot"] / 2, SPK_FACE - 1, SPK_FACE + 4.0, hx, hy))
            adds.append(boss)
    rim_o = box(sp["cx"] - 27.0, sp["cx"] + 27.0, sp["cy"] - 13.0, sp["cy"] + 13.0, SPK_FACE, Z_IN + 0.5)
    rim_i = box(sp["cx"] - 25.6, sp["cx"] + 25.6, sp["cy"] - 11.6, sp["cy"] + 11.6, SPK_FACE - 1, Z_IN + 1)
    adds.append(rim_o.cut(rim_i))

    # LED 라이트파이프 자리
    lx, ly = LED_SLOT["cx"], LED_SLOT["cy"]
    adds.append(box(lx - 11.6, lx + 11.6, ly - 4.1, ly + 4.1, Z_IN - 2.0, Z_IN + 0.5).cut(
        box(lx - 10.4, lx + 10.4, ly - 2.9, ly + 2.9, Z_IN - 3, Z_IN + 1)))

    # 벽 브래킷 갈고리가 들어가는 혀 (위쪽 좌우). 갈고리 밑 45° 모따기를 피해 혀 끝 위 모서리를 따냄
    for hx in HOOK_X:
        t = box(hx - 5, hx + 5, HOOK_Y0 + 4.4, H, PLATE_T + CLEAR, PLATE_T + 4.4 - CLEAR + 0.0)
        t = t.cut(hook_wedge(hx, grow=CLEAR))
        # 출력용: 혀 앞쪽(+Z)에 45° 받침 — 갈고리 지붕(y < HOOK_Y0 + 10) 뒤에서 시작해 위 벽까지
        y_s, z_s = HOOK_Y0 + 10.0 + 0.6, PLATE_T + 4.4 - CLEAR
        gus = (cq.Workplane("YZ", origin=(hx - 5, 0, 0))
               .polyline([(y_s, z_s - 0.01), (H + 1, z_s - 0.01), (H + 1, z_s + (H + 1 - y_s))]).close()
               .extrude(10).val())
        t = t.fuse(gus)
        adds.append(t.intersect(outer_s))

    for a in adds:
        shell = shell.fuse(a)
    # 바깥으로 삐져나온 것이 없도록 외곽으로 한 번 자르고, 다시 구멍류 재적용은 불필요(내부만 추가했음)
    shell = shell.intersect(outer_s)
    # 벽 브래킷 아랫단(스커트)이 들어갈 자리: 아래쪽 뒤 테두리를 따냄
    shell = shell.cut(box(-60, 60, -1, PLATE_SKIRT + CLEAR, -1, PLATE_T + CLEAR))
    return shell.clean()


# ──────────────────────────────────────────────────────────────
# 02 LCD + Pi 섀시
# ──────────────────────────────────────────────────────────────
FRAME_SCREWS = [(sx * 36.0, y) for sx in (-1, 1) for y in (60.0, 120.0)]


def pi_world(lx, ly) -> tuple[float, float]:
    """Pi 기판 로컬(x: 길이, y: 폭) → 월드 (X, Y).
    부품면이 앞(+Z), USB/LAN 이 위, USB-C 가장자리(ly=0)가 오른쪽(+X), GPIO 가 왼쪽."""
    return PI["wid"] / 2 - ly, PI_Y0 + lx


def lcd_header_box(z0, z1, grow=0.0) -> cq.Shape:
    gx, _ = pi_world(0, 52.5)             # LCD 헤더는 Pi GPIO 바로 위
    x0 = gx - 2.54 - grow
    x1 = gx + 2.54 + grow
    y0 = PI_Y0 + LCD["hdr_from_end"] - grow
    y1 = y0 + LCD["hdr_len"] + 2 * grow
    return box(x0, x1, y0, y1, z0, z1)


HDMI_Y = PI_Y0 + 26.0                 # Pi micro-HDMI0 중심 (월드 Y 77.5), LCD HDMI 도 같은 높이
HDMI_KEEP = (29.05, 44.0, HDMI_Y - 8.0, HDMI_Y + 8.5, PI_TOP - 1.5, LCD_PCB_BACK + 1.5)  # FPC 케이블 + 양쪽 90° 플러그


def lcd_hdmi_box(grow=0.0) -> cq.Shape:
    x1 = WINDOW["cx"] + LCD["pcb_w"] / 2
    return box(x1 - LCD["hdmi_d"] - grow, x1 + 0.5 + grow,
               HDMI_Y - LCD["hdmi_w"] / 2 - grow, HDMI_Y + LCD["hdmi_w"] / 2 + grow,
               LCD_PCB_BACK - LCD["hdmi_t"] - grow, LCD_PCB_BACK)


def build_frame() -> cq.Shape:
    cx, cy = WINDOW["cx"], WINDOW["cy"]
    pw, ph = LCD["pcb_w"] + 0.4, LCD["pcb_h"] + 0.4
    ow, oh = pw + 8.0, ph + 8.0
    lip = 2.2
    frame = rrect(ow, oh, 3.0, FRAME_BACK, FRAME_FRONT, cx, cy).val()
    frame = frame.cut(rrect(pw - 2 * lip, ph - 2 * lip, 2.0, FRAME_BACK - 1, FRAME_FRONT + 1, cx, cy).val())
    # LCD 헤더 자리 비우기 (바깥 레일은 남김)
    frame = frame.cut(lcd_header_box(FRAME_BACK - 1, FRAME_FRONT + 1, grow=1.0)
                      .intersect(box(cx - pw / 2 + 0.01, 60, 0, H, -10, 60)))
    # 오른쪽 레일: LCD HDMI 단자 + 케이블 자리 비우기
    frame = frame.cut(box(LCD["pcb_w"] / 2 - LCD["hdmi_d"] - 1.0, 45, HDMI_Y - 8.5, HDMI_Y + 9.5, FRAME_BACK - 1, FRAME_FRONT + 1))
    # 위쪽 레일: Pi USB/LAN 위로 지나가므로 앞쪽 2.5 mm 만 남긴다
    frame = frame.cut(box(-60, 60, cy + ph / 2 - lip - 4.0, H, FRAME_BACK - 1, FRAME_FRONT - 2.5))
    # Pi 고정 가로바 2개 (GPIO 헤더 몸체 lx 5.83~58.17 을 피함, LCD 뒷면 부품 피해 얇게)
    for lx0, lx1 in ((0.0, 5.2), (58.8, 64.5)):
        _, y0 = pi_world(lx0, 0)
        _, y1 = pi_world(lx1, 0)
        frame = frame.fuse(box(cx - ow / 2 + 0.5, cx + ow / 2 - 0.5, y0, y1, FRAME_BACK, BAR_FRONT))
        # 출력용: LCD 뒷면 부품이 없는 곳은 가로바를 LCD 뒷면까지 채워 기둥으로 만든다 (긴 브리지 줄이기)
        lcd_parts = box(cx - 22.5, cx + 20.5, cy - 36.5, cy + 36.5, FRAME_BACK - 1, FRAME_FRONT + 1)
        full = box(cx - ow / 2 + 0.5, cx + ow / 2 - 0.5, y0, y1, BAR_FRONT - 0.01, FRAME_FRONT).cut(lcd_parts)
        full = full.cut(lcd_header_box(FRAME_BACK - 1, FRAME_FRONT + 1, grow=1.0))
        frame = frame.fuse(full)
    # 귀 (쉘 보스에 M3 고정)
    for x, y in FRAME_SCREWS:
        frame = frame.fuse(rrect(12.0, 9.0, 3.0, FRAME_BACK, FRAME_FRONT, x - math.copysign(2.0, x), y).val())
    for x, y in FRAME_SCREWS:
        frame = frame.cut(cyl(1.7, FRAME_BACK - 1, FRAME_FRONT + 1, x, y))
    # Pi 스탠드오프 (M2.5 셀프태핑 ø2.2). GPIO 쪽 두 개는 헤더 몸체 쪽을 D 자로 깎는다
    for lx, ly in PI["holes"]:
        x, y = pi_world(lx, ly)
        so = cyl(3.0, PI_TOP, FRAME_BACK + 0.5, x, y)
        if ly > 30:
            _, yc = pi_world(5.6 if lx < 30 else 58.4, 0)
            keep = box(-60, 60, -10, yc, -10, 60) if lx < 30 else box(-60, 60, yc, H + 10, -10, 60)
            so = so.intersect(keep)
        frame = frame.fuse(so)
        frame = frame.cut(cyl(1.1, PI_TOP - 0.1, FRAME_BACK + 0.6, x, y))
    return frame.clean()


# ──────────────────────────────────────────────────────────────
# 03 벽 브래킷
# ──────────────────────────────────────────────────────────────
HOOK_X = (-36.0, 36.0)
HOOK_Y0 = H - 32.0               # 갈고리 다리 아래끝 (위 벽에서 32 mm)
HOOK_CH = 2.5                     # 갈고리 지붕 밑 45° 모따기 크기


def hook_wedge(hx, grow=0.0) -> cq.Shape:
    """갈고리 다리와 지붕 사이 45° 삼각 기둥 (YZ 단면). grow 는 쉘 혀를 깎을 때 쓰는 틈"""
    y0, z1 = HOOK_Y0 + 4.0, PLATE_T + 4.4
    c = HOOK_CH + grow
    pts = [(y0 - 1.0, z1 - c - 1.0), (y0 + c, z1), (y0 + c, z1 + 1.0), (y0 - 1.0, z1 + 1.0)]
    if grow == 0.0:
        pts = [(y0 - 0.01, z1 - c), (y0 - 0.01, z1 + 0.01), (y0 + c, z1 + 0.01)]
    w = cq.Workplane("YZ", origin=(hx - 5, 0, 0)).polyline(pts).close().extrude(10)
    return w.val()


def build_plate() -> cq.Shape:
    wi, hi, ri = plan(-T - CLEAR)
    plate = rrect(wi, hi, ri, 0, PLATE_T, cy=H / 2).val()
    # 아랫단 스커트: 쉘 바깥 윤곽(-0.4)까지 넓혀 뒷면을 끝까지 막는다. 바깥 아래 모서리는 쉘과 같은 R 처리
    wo, ho, ro = plan(-CLEAR)
    skirt = (rrect(wo, ho, ro, 0, PLATE_T, cy=H / 2).edges("<Z").fillet(F_BACK)
             .val().intersect(box(-60, 60, -1, PLATE_SKIRT, -1, PLATE_T + 1)))
    plate = plate.fuse(skirt)
    # 쉘 바닥의 납작 케이블 홈과 같은 자리를 비움
    plate = plate.cut(box(11.6, 24.4, -1, 5.0, -1, PLATE_T + 1))
    # 벽 고정 나사: ø4 접시머리 → 구멍 ø4.6, 90° 접시 자리 ø9.4
    hr, cr = FASTENERS["wall_hole"] / 2, FASTENERS["wall_csk"] / 2
    for y in WALL_SCREW_Y:
        plate = plate.cut(cyl(hr, -1, PLATE_T + 1, 0, y))
        plate = plate.cut(cq.Solid.makeCone(hr, cr, cr - hr, V(0, y, PLATE_T - (cr - hr) + 0.01), V(0, 0, 1)))
    # 벽 타공 전원선 구멍
    plate = plate.cut(cyl(8.0, -1, PLATE_T + 1, 0, POWER_Y))
    # 갈고리 (ㄴ자: 다리 + 위로 선 판)
    for hx in HOOK_X:
        plate = plate.fuse(box(hx - 5, hx + 5, HOOK_Y0, HOOK_Y0 + 4, PLATE_T - 0.01, PLATE_T + 4.4))
        plate = plate.fuse(box(hx - 5, hx + 5, HOOK_Y0, HOOK_Y0 + 10, PLATE_T + 4.4, PLATE_T + 7.4))
        plate = plate.fuse(hook_wedge(hx))      # 갈고리 지붕 밑 45° 모따기 → 서포트 없이 출력
    # 바닥 잠금 보스 (M3 x 16 기계나사가 ø2.5 구멍에 직접 나사산을 내며 들어감, 아래에서 위로)
    y_bot = T + CLEAR + SLIDE
    boss = box(2.0, 10.0, y_bot, y_bot + 10.0, PLATE_T - 0.01, 11.0)
    boss = boss.cut(cq.Solid.makeCylinder(FASTENERS["m3_pilot"] / 2, 9.5, V(6, y_bot - 0.1, 7), V(0, 1, 0)))
    plate = plate.fuse(boss)
    return plate.clean()


# ──────────────────────────────────────────────────────────────
# 04 블랙 바이저, 05 라이트파이프
# ──────────────────────────────────────────────────────────────
def build_visor() -> cq.Shape:
    v = VISOR
    vis = pill(v["w"] - 0.3, v["h"] - 0.3, D - v["depth"], D, v["cx"], v["cy"])
    vis = vis.cut(lens_cut())
    tx, ty = TOF_POS
    sens_front = Z_IN - 0.2
    grow = (D - sens_front + 0.5) * math.tan(math.radians(TOF["fov_half"]))
    vis = vis.cut(frustum(TOF["sens_w"] + 1.0, TOF["sens_h"] + 1.0, 0.6, sens_front,
                          TOF["sens_w"] + 1.0 + 2 * grow, TOF["sens_h"] + 1.0 + 2 * grow, 1.5, D + 0.5, tx, ty))
    return vis.clean()


def build_light_pipe() -> cq.Shape:
    ls = LED_SLOT
    bar = pill(ls["w"] - 0.3, ls["h"] - 0.3, Z_IN - 0.01, D, ls["cx"], ls["cy"])
    flange = box(ls["cx"] - 10.2, ls["cx"] + 10.2, ls["cy"] - 2.7, ls["cy"] + 2.7, Z_IN - 1.2, Z_IN)
    return bar.fuse(flange).clean()


# ──────────────────────────────────────────────────────────────
# 실제 부품 (간섭 검사·렌더용, 출력하지 않음)
# ──────────────────────────────────────────────────────────────
def components() -> dict[str, cq.Shape]:
    c: dict[str, cq.Shape] = {}

    def pbox(lx0, lx1, ly0, ly1, h, z_from=None):
        x0, y0 = pi_world(lx0, ly0)
        x1, y1 = pi_world(lx1, ly1)
        zf = PI_TOP if z_from is None else z_from
        return box(min(x0, x1), max(x0, x1), min(y0, y1), max(y0, y1), zf, zf + h)

    pi = rrect(PI["wid"], PI["len"], 3.0, PI_BOTTOM, PI_TOP, 0, PI_Y0 + PI["len"] / 2).val()
    for lx, ly in PI["holes"]:
        x, y = pi_world(lx, ly)
        pi = pi.cut(cyl(PI["hole_d"] / 2, PI_BOTTOM - 1, PI_TOP + 1, x, y))
    parts = [
        pbox(70.0, 87.1, 2.4, 15.6, 16.0),       # USB 2.0/3.0 스택 x2
        pbox(70.0, 87.1, 20.4, 33.6, 16.0),
        pbox(65.6, 87.1, 37.75, 53.75, 13.5),    # 이더넷
        pbox(5.83, 39.6, 49.96, 55.04, LCD_PCB_BACK - LCD["hdr_h"] - PI_TOP),  # GPIO 1~26 + 2×13 스태킹 헤더
        pbox(39.6, 58.17, 49.96, 55.04, 8.5),    # GPIO 27~40 (Pi 기본 핀, 비어 있음)
        pbox(21.5, 36.5, 24.5, 39.5, 9.5),       # SoC + 방열판 14x14x8
        pbox(7.7, 14.7, -1.0, 6.5, 3.3),         # USB-C
        pbox(22.5, 29.5, -1.0, 6.5, 3.0),        # micro HDMI x2
        pbox(36.0, 43.0, -1.0, 6.5, 3.0),
        pbox(50.0, 57.0, -2.0, 12.5, 6.0),       # 오디오 잭
        pbox(42.0, 48.0, 1.0, 23.0, 5.5),        # CSI 커넥터
    ]
    for p in parts:
        pi = pi.fuse(p)
    # 납땜면(벽 쪽) 돌출: GPIO 핀 끝, microSD
    pi = pi.fuse(pbox(5.83, 58.17, 49.96, 55.04, 2.0, z_from=PI_BOTTOM - 2.0))
    pi = pi.fuse(pbox(-2.5, 12.0, 22.0, 34.0, 1.5, z_from=PI_BOTTOM - 1.5))
    c["Raspberry Pi 4"] = pi
    # L형 USB-C 플러그 (오른쪽으로 꺾임)
    x, y = pi_world(11.2, 0)
    c["USB-C L형 플러그"] = box(x + 1.05, x + 12.0, y - 6.0, y + 6.0, PI_TOP - 2.0, PI_TOP + 8.0)

    # LCD
    cx, cy = WINDOW["cx"], WINDOW["cy"]
    lcd = box(cx - LCD["pcb_w"] / 2, cx + LCD["pcb_w"] / 2, cy - LCD["pcb_h"] / 2, cy + LCD["pcb_h"] / 2,
              LCD_PCB_BACK, LCD_PCB_FRONT)
    lcd = lcd.fuse(box(cx - LCD["glass_w"] / 2, cx + LCD["glass_w"] / 2, cy - LCD["glass_h"] / 2, cy + LCD["glass_h"] / 2,
                       LCD_PCB_FRONT, LCD_FRONT))
    lcd = lcd.fuse(box(cx - 22, cx + 20, cy - 36, cy + 36, LCD_PCB_BACK - LCD["back_t"], LCD_PCB_BACK))
    lcd = lcd.fuse(lcd_header_box(LCD_PCB_BACK - LCD["hdr_h"], LCD_PCB_BACK))
    lcd = lcd.fuse(lcd_hdmi_box())
    c["3.5인치 HDMI LCD"] = lcd

    # micro-HDMI → HDMI FPC 케이블 (양쪽 90° 플러그 + 리본). 실제 모양 대신 차지하는 공간
    c["HDMI FPC 케이블(공간)"] = box(*HDMI_KEEP)

    # GPIO 27~40 배선 공간: ㄱ자(90°) 암 듀폰 또는 납땜 전선이 왼쪽으로 빠짐
    gx0, gy0 = pi_world(39.6, 55.04)
    gx1, gy1 = pi_world(58.17, 49.96)
    ylo, yhi = min(gy0, gy1), max(gy0, gy1)
    c["GPIO 27~40 배선(공간)"] = box(-40.0, gx0 - 0.05, ylo, yhi, PI_TOP + 0.5, PI_TOP + 10.5).fuse(
        box(gx0 - 0.05, gx1, ylo, yhi, PI_TOP + 8.55, PI_TOP + 10.5))   # 핀 위 하우징 + 왼쪽으로 빠지는 전선
    # LCD 화면(표시용, 간섭 검사 제외)
    c["_LCD 화면"] = box(cx - LCD["act_w"] / 2, cx + LCD["act_w"] / 2, cy - LCD["act_h"] / 2, cy + LCD["act_h"] / 2,
                       LCD_FRONT - 0.01, LCD_FRONT)

    # 카메라
    top = CAM["lens_from_top"]
    cam = box(-CAM["w"] / 2, CAM["w"] / 2, top - CAM["h"], top, -CAM["pcb"], 0)
    for hx, hy in cam_holes_local():
        cam = cam.cut(cq.Solid.makeCylinder(1.1, 3, V(hx, hy, -2), V(0, 0, 1)))
    cam = cam.fuse(box(-4.5, 4.5, -4.5, 4.5, 0, 5.0))
    cam = cam.fuse(cq.Solid.makeCylinder(CAM["barrel"] / 2, CAM["height"] - CAM["pcb"] - 5.0, V(0, 0, 5.0), V(0, 0, 1)))
    cam = cam.fuse(box(-10.5, 10.5, top - CAM["h"], top - CAM["h"] + 6, -CAM["pcb"] - 2.5, -CAM["pcb"]))  # FPC 커넥터
    c["Camera Module 3 Wide"] = cam_place(cam)
    lens = box(-4.5, 4.5, -4.5, 4.5, 0, 5.0).fuse(
        cq.Solid.makeCylinder(CAM["barrel"] / 2, CAM["height"] - CAM["pcb"] - 5.0, V(0, 0, 5.0), V(0, 0, 1)))
    c["_cam_lens"] = cam_place(lens)
    c["_cam_board"] = cam_place(cam.cut(lens))

    # ToF (VL53L0X V2 보드): 센서 칩이 쉘 안쪽 면에서 0.2 뒤
    tx, ty = TOF_POS
    sf = Z_IN - 0.2
    bf = sf - TOF["sens_t"]
    tof = box(tx - TOF["w"] / 2, tx + TOF["w"] / 2, ty - TOF["h"] / 2, ty + TOF["h"] / 2, bf - TOF["pcb"], bf)
    tof = tof.fuse(box(tx - TOF["sens_w"] / 2, tx + TOF["sens_w"] / 2, ty - TOF["sens_h"] / 2, ty + TOF["sens_h"] / 2, bf, sf))
    c["VL53L5CX ToF"] = tof
    c["_tof_sensor"] = box(tx - TOF["sens_w"] / 2, tx + TOF["sens_w"] / 2, ty - TOF["sens_h"] / 2, ty + TOF["sens_h"] / 2, bf, sf)
    c["_tof_board"] = tof.cut(c["_tof_sensor"])
    # Rev E.2/F.2: ToF 핀은 선을 직접 납땜 (뒤에 사운드카드 스틱이 지나가서 일자 핀헤더 공간 없음)

    # USB 포트 위쪽 단 (USB2 = ly 2.4~15.6, USB3 = ly 20.4~33.6), 포트 입구 y = Pi 끝 + 2.1
    port_y = PI_Y0 + 87.1
    upper_z = PI_TOP + 11.5                               # 위쪽 포트 중심 높이

    # USB 핀마이크(JMTek) → USB 3.0 위쪽 포트 (Rev E.2/F.2)
    ux, _ = pi_world(0, 27.0)
    c["USB 핀마이크"] = box(ux - UMIC["w"] / 2, ux + UMIC["w"] / 2, port_y, port_y + UMIC["len"],
                         upper_z - UMIC["t"] / 2, upper_z + UMIC["t"] / 2)

    # USB 사운드카드 스틱 (Rev E.2/F.2): 포트에 바로 꽂으면 스틱 끝(3.5 mm 잭)이 윗벽에서 3 mm라 플러그가 못 들어감
    #   → 15~20 cm USB 연장선으로 빼서, 오른쪽 옆벽 안쪽에 세워(18 mm가 깊이 방향) 폼테이프로 붙임. 잭은 아래(스피커 쪽)
    sx_, _ = pi_world(0, 9.0)
    lz = PI_TOP + 4.5
    xs1 = W / 2 - T - 1.0                                  # 옆벽 안쪽 - 폼테이프 1 mm
    c["USB 사운드카드 스틱"] = box(xs1 - USB_SND["t"], xs1, SND_Y0, SND_Y0 + USB_SND["len"],
                                SND_Z - USB_SND["w"] / 2, SND_Z + USB_SND["w"] / 2)
    # 연장선 암 단자(스틱 USB 플러그 12 mm를 덮음) + 꺾이는 선 + Pi 쪽 수 플러그 → 비워 둘 공간
    hy0 = SND_Y0 + USB_SND["len"] - 12.0
    ext = box(xs1 - USB_SND["t"] - 0.2, xs1 + 0.2, hy0, hy0 + 34.0, SND_Z - 9.5, SND_Z + 9.5)
    ext = ext.fuse(box(sx_ - 8.0, sx_ + 8.0, port_y, port_y + 21.0, lz - 4.5, lz + 4.5))       # 수 플러그 (USB 2.0 아래 포트)
    ext = ext.fuse(box(sx_ + 8.0, xs1 - USB_SND["t"], port_y + 3.0, port_y + 15.0, 6.0, 16.0))  # 선이 꺾여 내려가는 자리 (위쪽 걸이 갈고리 아래)
    c["USB 연장선(공간)"] = ext.cut(c["USB 사운드카드 스틱"])   # 스틱 플러그가 들어간 부분은 빼고
    # 스피커 선 3.5 mm 플러그 (ㄱ자 권장) — 스틱 아래 끝
    c["3.5mm 플러그(공간)"] = cq.Solid.makeCylinder(4.5, 18.0, V(xs1 - USB_SND["t"] / 2, SND_Y0 - 18.0, SND_Z), V(0, 1, 0))

    # 상자형 스피커 (앞판 69.9 x 31, 깊이 16.5, 아래 선 턱 11 x 5)
    sp = SPEAKER
    spk = box(sp["cx"] - sp["L"] / 2, sp["cx"] + sp["L"] / 2, sp["cy"] - sp["h"] / 2, sp["cy"] + sp["h"] / 2,
              SPK_FACE - sp["flange"], SPK_FACE)                                  # 나사 구멍 있는 앞판
    spk = spk.fuse(box(sp["cx"] - sp["body_L"] / 2, sp["cx"] + sp["body_L"] / 2, sp["cy"] - sp["h"] / 2, sp["cy"] + sp["h"] / 2,
                       SPK_FACE - sp["depth"], SPK_FACE - sp["flange"] + 0.01))    # 뒤 상자 (귀 부분 없음)
    for sx in (-1, 1):
        for sy in (-1, 1):
            spk = spk.cut(cyl(sp["hole_d"] / 2, SPK_FACE - 3, SPK_FACE + 1,
                              sp["cx"] + sx * sp["hole_sx"] / 2, sp["cy"] + sy * sp["hole_sy"] / 2))
    spk = spk.fuse(box(sp["cx"] + sp["body_L"] / 2 - 13.0, sp["cx"] + sp["body_L"] / 2 - 2.0, sp["cy"] - sp["h"] / 2 - 4.0,
                       sp["cy"] - sp["h"] / 2 + 0.01, SPK_FACE - sp["depth"], SPK_FACE - sp["depth"] + 9.0))
    c["스피커 70x31 (4Ω 3W)"] = spk

    # 버튼
    bx, by = BUTTON["cx"], BUTTON["cy"]
    btn = cyl(BTN["head"] / 2, D, D + BTN["head_t"], bx, by)
    btn = btn.fuse(cyl(BTN["body"] / 2 - 0.15, Z_IN - BTN["length"], D, bx, by))
    btn = btn.fuse(cyl(BTN["nut"] / 2, Z_IN - BTN["nut_t"], Z_IN, bx, by))
    c["16mm 호출벨"] = btn

    # LED (3 mm)
    lx, ly = LED_SLOT["cx"], LED_SLOT["cy"]
    c["상태 LED"] = box(lx - 2.5, lx + 2.5, ly - 2.5, ly + 2.5, Z_IN - 1.2 - 3.0, Z_IN - 1.2)
    c.update(fasteners())
    return c


def _screw(d, length, head_d, head_h, at: V, axis: V) -> cq.Shape:
    """냄비머리 나사: at = 머리 밑면 중심, axis = 나사가 들어가는 방향"""
    axis = axis.normalized()
    shank = cq.Solid.makeCylinder(d / 2, length, at, axis)
    head = cq.Solid.makeCylinder(head_d / 2, head_h, at - axis * head_h, axis)
    return shank.fuse(head).clean()


# 나사가 정상적으로 파고드는 상대 부품 (간섭 검사에서 제외, 대신 물림 길이를 따로 보고)
SCREW_HOSTS = {
    "M3 인서트": "01_front_shell",
    "M2.5x6 태핑 (Pi)": "02_lcd_pi_chassis",
    "M2x5 태핑 (카메라)": "06_camera_holder",
    "M3x16 (바닥 잠금)": "03_wall_plate",
    "M2.5x6 태핑 (스피커)": "01_front_shell",
}


def fasteners() -> dict[str, cq.Shape]:
    f = FASTENERS
    out: dict[str, list[cq.Shape]] = {k: [] for k in
                                      ("M3x10 (섀시)", "M3 인서트", "M2.5x6 태핑 (Pi)", "M2x5 태핑 (카메라)",
                                       "M3x16 (바닥 잠금)", "ø4x25 접시 (벽)", "M2.5x6 태핑 (스피커)")}
    ins = f["m3_insert"]
    for x, y in FRAME_SCREWS:
        out["M3x10 (섀시)"].append(_screw(3.0, 10.0, *f["m3_head"], V(x, y, FRAME_BACK), V(0, 0, 1)))
        out["M3 인서트"].append(cyl(ins["od"] / 2, FRAME_FRONT, FRAME_FRONT + ins["length"], x, y)
                              .cut(cyl(1.5, FRAME_FRONT - 1, FRAME_FRONT + ins["length"] + 1, x, y)))
    for lx, ly in PI["holes"]:
        x, y = pi_world(lx, ly)
        out["M2.5x6 태핑 (Pi)"].append(_screw(2.5, 6.0, *f["m25_head"], V(x, y, PI_BOTTOM), V(0, 0, 1)))
    for hx, hy in cam_holes_local():
        out["M2x5 태핑 (카메라)"].append(cam_place(_screw(2.0, 5.0, *f["m2_head"], V(hx, hy, -CAM["pcb"]), V(0, 0, 1))))
    sp = SPEAKER
    for sx in (-1, 1):
        for sy in (-1, 1):
            hx, hy = sp["cx"] + sx * sp["hole_sx"] / 2, sp["cy"] + sy * sp["hole_sy"] / 2
            out["M2.5x6 태핑 (스피커)"].append(_screw(2.5, 6.0, *f["m25_head"], V(hx, hy, SPK_FACE - sp["flange"]), V(0, 0, 1)))
    out["M3x16 (바닥 잠금)"].append(_screw(3.0, 16.0, *f["m3_head"], V(6, 1.2, 7), V(0, 1, 0)))
    for y in WALL_SCREW_Y:
        head = cq.Solid.makeCone(4.0, 2.0, 2.0, V(0, y, PLATE_T), V(0, 0, -1))
        out["ø4x25 접시 (벽)"].append(head.fuse(cq.Solid.makeCylinder(2.0, 23.0, V(0, y, PLATE_T - 2.0), V(0, 0, -1))))
    res = {}
    for k, v in out.items():
        s = v[0]
        for o in v[1:]:
            s = s.fuse(o)
        res[k] = s.clean()
    return res


def build_all():
    parts = {
        "01_front_shell": build_shell(),
        "02_lcd_pi_chassis": build_frame(),
        "03_wall_plate": build_plate(),
        "04_black_visor": build_visor(),
        "05_led_light_pipe": build_light_pipe(),
        "06_camera_holder": build_cam_holder(),
    }
    return parts, components()
