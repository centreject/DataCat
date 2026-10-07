"""
DataCat 무인현관 초인종 외함 — Rev D (Claude)

Rev D 변경: 새 부품표 반영
  - INMP441 마이크·MAX98357A 앰프 삭제 → USB 마이크 동글(USB2 포트), USB 스피커(USB3 포트)
  - SPI LCD → Waveshare 3.5inch HDMI LCD (HDMI 단자 오른쪽 가장자리, GPIO 5V 전원)
  - micro-HDMI → HDMI 연결: 스태킹 높이 때문에 U자 어댑터 대신 짧은 FPC(리본) 케이블, 공간 확보
  - GPIO 스태킹 헤더는 2×13 (1~26번 핀) → 27~40번 핀이 LCD 아래에서 비어 있음

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
W, H, D = 105.0, 215.0, 42.0      # 가로, 세로, 깊이
R_PLAN = 40.0                     # 정면에서 본 모서리 반경 (알약형)
T = 2.5                           # 쉘 두께
F_FRONT = 14.0                    # 전면 테두리 라운드 (레퍼런스처럼 둥글게)
F_BACK = 1.5                      # 벽쪽 테두리 라운드
Z_IN = D - T                      # 전면 안쪽 면 z = 39.5

# 전면 요소 위치
VISOR = dict(cx=0.0, cy=177.0, w=72.0, h=24.0, depth=1.2)
PANEL = dict(cx=0.0, cy=83.0, w=70.0, h=134.0, r=16.0, groove=1.2, gdepth=0.8)
WINDOW = dict(cx=0.0, cy=94.0, w=49.5, h=74.0, r=2.0, chamfer=1.2)
LED_SLOT = dict(cx=0.0, cy=141.0, w=16.0, h=2.0)
BUTTON = dict(cx=-8.0, cy=33.0, hole=16.3)
SPEAKER = dict(cx=21.0, cy=33.0, dia=28.0, depth=8.0)
GRILLE = dict(cx=21.0, cy=33.0, cols=5, rows=4, pitch=3.4, hole=1.7)

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
CAM = dict(w=25.0, h=24.0, pcb=1.0, height=12.4, lens_from_top=9.6,
           hole_dx=10.5, hole_rows=(2.0, 14.5), lens_glass=5.75, barrel=8.6,
           fov_half=62.0, tilt=10.0)   # tilt: 아래로 숙이는 각도 (기획서 10~15° 후보)
# SparkFun Qwiic Mini ToF Imager (VL53L5CX) : 12.7 x 25.4, 센서 6.4 x 3.0 x 1.75
TOF = dict(w=12.7, h=25.4, pcb=1.6, sens_w=6.4, sens_h=3.0, sens_t=1.75, back=3.5, fov_half=30.0)
# USB 미니 마이크 동글 (무지향, 예: Adafruit #3367 류) : 22.5 x 18.3 x 7.7, 포트 밖으로 ~10.5 돌출
UMIC = dict(len=10.5, w=18.3, t=7.7)
# USB 스피커 (2~3 W, USB 하나로 전원·소리) : 케이스를 열어 ø28 유닛은 그릴 뒤 링에,
# USB 사운드 보드는 유닛 뒤 공간에 양면 폼테이프로 고정. 유닛 지름은 도착 후 실측해 SPEAKER["dia"] 수정
USPK_BOARD = dict(x0=10.0, x1=38.0, y0=16.0, y1=44.0, z0=14.0, z1=29.0)
# 16 mm 메탈 푸시버튼 + LED 링 : 패널 구멍 ø16, 헤드 ø18, 너트 22 mm, 패널 뒤 길이 ~32
BTN = dict(head=18.0, head_t=2.0, body=16.0, nut=24.0, nut_t=4.0, length=32.0)

# 부품 배치 (월드 좌표)
VIS_Y = VISOR["cy"]
CAM_POS = (-20.0, VIS_Y)          # 렌즈 중심
TOF_POS = (20.0, VIS_Y)           # 센서 중심
MIC_HOLES = [(19.0 + dx, 156.0) for dx in (-3.0, 0.0, 3.0)]   # USB 마이크 동글 앞 소리 구멍

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

# 벽 브래킷
PLATE_T = 3.0
CLEAR = 0.4
SLIDE = 7.4                       # 걸고 내려 끼우는 이동량
# Rev D.1: 벽 브래킷 아래쪽(Y < PLATE_SKIRT)은 쉘 바깥 윤곽까지 넓혀 뒷면 아래 틈을 막는다.
# 그만큼 쉘 뒤 테두리를 아래쪽에서 PLATE_T + CLEAR 깊이로 따내서, 쉘을 올린 채 벽에 대도 걸리지 않는다.
PLATE_SKIRT = 40.0


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
LENS_FRONT_Z = D - 0.8            # 렌즈 앞면: 바이저 표면에서 0.8 안쪽


def cam_place(shape: cq.Shape) -> cq.Shape:
    """카메라 로컬(렌즈 중심 원점, 기판 앞면 z=0, 시선 +z) → 월드"""
    lens_h = CAM["height"] - CAM["pcb"]           # 기판 앞면에서 렌즈 앞까지 11.4
    s = shape.translate(V(0, 0, -lens_h))         # 렌즈 앞면 중심을 원점으로
    s = s.rotate(V(0, 0, 0), V(1, 0, 0), CAM["tilt"])   # +X축 회전 → 시선이 아래로
    return s.translate(V(CAM_POS[0], CAM_POS[1], LENS_FRONT_Z))


def cam_dir() -> V:
    a = math.radians(CAM["tilt"])
    return V(0, -math.sin(a), math.cos(a))


def cam_holes_local():
    top = CAM["lens_from_top"]
    return [(sx * CAM["hole_dx"], top - row) for sx in (-1, 1) for row in CAM["hole_rows"]]


def lens_bevel() -> cq.Shape:
    """렌즈 구멍 바깥 45° 모따기 (레퍼런스의 렌즈 링 느낌)"""
    r = CAM["barrel"] / 2 + 0.5
    return cq.Solid.makeCone(r, r + 1.4, 1.4, V(CAM_POS[0], CAM_POS[1], D - 1.4 + 0.001), V(0, 0, 1)).fuse(
        cyl(r + 1.4, D - 0.001, D + 1, CAM_POS[0], CAM_POS[1]))


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

    # ── 호출벨 구멍 ──
    shell = shell.cut(cyl(BUTTON["hole"] / 2, Z_IN - 1, D + 1, BUTTON["cx"], BUTTON["cy"]))

    # ── 스피커 그릴 ──
    g = GRILLE
    for i in range(g["cols"]):
        for j in range(g["rows"]):
            x = g["cx"] + (i - (g["cols"] - 1) / 2) * g["pitch"]
            y = g["cy"] + (j - (g["rows"] - 1) / 2) * g["pitch"]
            shell = shell.cut(cyl(g["hole"] / 2, Z_IN - 1, D + 1, x, y))

    # ── 카메라 렌즈 구멍 (기울어진 축을 따라 원통 + 화각 원뿔) ──
    d = cam_dir()
    lens_c = V(CAM_POS[0], CAM_POS[1], LENS_FRONT_Z)
    barrel_r = CAM["barrel"] / 2 + 0.5
    shell = shell.cut(cq.Solid.makeCylinder(barrel_r, 12, lens_c - d * 6, d))
    cone_h = 6.0
    shell = shell.cut(cq.Solid.makeCone(CAM["lens_glass"] / 2 + 0.3,
                                        CAM["lens_glass"] / 2 + 0.3 + cone_h * math.tan(math.radians(CAM["fov_half"])),
                                        cone_h, lens_c, d))

    shell = shell.cut(lens_bevel())

    # ── ToF 창 (화각 30°로 벌어지는 사각 창) ──
    tx, ty = TOF_POS
    sens_front = Z_IN - 0.2
    grow = (D - sens_front + 0.5) * math.tan(math.radians(TOF["fov_half"]))
    shell = shell.cut(frustum(TOF["sens_w"] + 0.4, TOF["sens_h"] + 0.4, 0.6, sens_front,
                              TOF["sens_w"] + 0.4 + 2 * grow, TOF["sens_h"] + 0.4 + 2 * grow, 1.5, D + 0.5,
                              tx, ty))

    # ── USB 마이크 소리 구멍 3개 ──
    for mx, my in MIC_HOLES:
        shell = shell.cut(cyl(0.7, Z_IN - 1, D + 1, mx, my))

    # ── 측면 통풍구 (Pi 높이, 양쪽 아래·위 그룹) ──
    for side in (-1, 1):
        for y0 in (66.0, 108.0):
            for k in range(6):
                y = y0 + k * 4.5
                # XY 평면의 알약을 Y축으로 90° 돌리면 길이 방향이 Z, 두께 방향이 X 가 된다
                slot = pill(16, 2.2, -5, 5, 0, 0).rotate(V(0, 0, 0), V(0, 1, 0), 90)
                shell = shell.cut(slot.translate(V(side * (W / 2 - T / 2), y, 19.0)))

    # ── 바닥: 케이블 홈(벽쪽) + 잠금 나사 구멍 ──
    shell = shell.cut(box(12, 24, -1, 4, -1, 5))
    shell = shell.cut(cq.Solid.makeCylinder(1.7, 6, V(6, -1, 7), V(0, 1, 0)))
    shell = shell.cut(cq.Solid.makeCylinder(3.3, 1.0, V(6, -0.1, 7), V(0, 1, 0)))

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

    # 섀시 고정 보스 (M3 열압입 인서트 ø4.0, 깊이 5.5)
    for x, y in FRAME_SCREWS:
        b = cyl(4.0, FRAME_FRONT, Z_IN + 0.5, x, y).cut(cyl(2.0, FRAME_FRONT - 0.1, FRAME_FRONT + 5.5, x, y))
        adds.append(b)

    # 카메라 보스 (기판 구멍 4개, M2 셀프태핑 ø1.8) — 기울기를 따라 만들고 벽 안쪽에서 자름
    for hx, hy in cam_holes_local():
        b = cq.Solid.makeCylinder(2.4, 16, V(hx, hy, 0), V(0, 0, 1)).cut(
            cq.Solid.makeCylinder(0.9, 7, V(hx, hy, -0.1), V(0, 0, 1)))
        b = cam_place(b).intersect(box(-60, 60, 0, H, 0, Z_IN + 0.5))
        adds.append(b)

    # ToF 위치 잡이 리브 (보드 13.1 x 25.8)
    tw, th = TOF["w"] + 0.4, TOF["h"] + 0.4
    tof_board_front = Z_IN - 0.2 - TOF["sens_t"]
    for sx in (-1, 1):
        for sy in (-1, 1):
            cx, cy = tx + sx * tw / 2, ty + sy * th / 2
            adds.append(box(min(cx, cx + sx * 1.2), max(cx, cx + sx * 1.2),
                            min(cy, cy - sy * 6), max(cy, cy - sy * 6), tof_board_front - 1.2, Z_IN + 0.5))

    # 스피커 링 (ø28)
    sx_, sy_ = SPEAKER["cx"], SPEAKER["cy"]
    sr = SPEAKER["dia"] / 2 + 0.3
    adds.append(cyl(sr + 1.5, Z_IN - 4, Z_IN + 0.5, sx_, sy_).cut(cyl(sr, Z_IN - 5, Z_IN + 1, sx_, sy_)))

    # USB 스피커 보드 받침: 오른쪽 아래 벽에서 나온 선반 (보드를 양면 폼테이프로 붙임)
    b = USPK_BOARD
    shelf = box(b["x0"] + 14, 60, b["y0"] + 2, b["y1"] - 2, b["z0"] - 2.0, b["z0"])
    adds.append(shelf)

    # LED 라이트파이프 자리
    lx, ly = LED_SLOT["cx"], LED_SLOT["cy"]
    adds.append(box(lx - 11.6, lx + 11.6, ly - 4.1, ly + 4.1, Z_IN - 2.0, Z_IN + 0.5).cut(
        box(lx - 10.4, lx + 10.4, ly - 2.9, ly + 2.9, Z_IN - 3, Z_IN + 1)))

    # 벽 브래킷 갈고리가 들어가는 혀 (위쪽 좌우)
    for hx in HOOK_X:
        t = box(hx - 5, hx + 5, HOOK_Y0 + 4.4, H, PLATE_T + CLEAR, PLATE_T + 4.4 - CLEAR + 0.0)
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
FRAME_SCREWS = [(sx * 36.0, y) for sx in (-1, 1) for y in (64.0, 124.0)]


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
HOOK_X = (-25.0, 25.0)
HOOK_Y0 = 183.0


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
    # 벽 고정 나사 (접시머리 ø4.5 / ø9)
    for y in (70.0, 165.0):
        plate = plate.cut(cyl(2.4, -1, PLATE_T + 1, 0, y))
        plate = plate.cut(cq.Solid.makeCone(2.4, 4.9, 2.5, V(0, y, PLATE_T - 2.5 + 0.01), V(0, 0, 1)))
    # 벽 타공 전원선 구멍
    plate = plate.cut(cyl(8.0, -1, PLATE_T + 1, 0, 118.0))
    # 갈고리 (ㄴ자: 다리 + 위로 선 판)
    for hx in HOOK_X:
        plate = plate.fuse(box(hx - 5, hx + 5, HOOK_Y0, HOOK_Y0 + 4, PLATE_T - 0.01, PLATE_T + 4.4))
        plate = plate.fuse(box(hx - 5, hx + 5, HOOK_Y0, HOOK_Y0 + 10, PLATE_T + 4.4, PLATE_T + 7.4))
    # 바닥 잠금 보스 (M3 x 20, 아래에서 위로)
    y_bot = T + CLEAR + SLIDE
    boss = box(2.0, 10.0, y_bot, y_bot + 10.0, PLATE_T - 0.01, 11.0)
    boss = boss.cut(cq.Solid.makeCylinder(1.25, 9.5, V(6, y_bot - 0.1, 7), V(0, 1, 0)))
    plate = plate.fuse(boss)
    return plate.clean()


# ──────────────────────────────────────────────────────────────
# 04 블랙 바이저, 05 라이트파이프
# ──────────────────────────────────────────────────────────────
def build_visor() -> cq.Shape:
    v = VISOR
    vis = pill(v["w"] - 0.3, v["h"] - 0.3, D - v["depth"], D, v["cx"], v["cy"])
    d = cam_dir()
    lens_c = V(CAM_POS[0], CAM_POS[1], LENS_FRONT_Z)
    vis = vis.cut(cq.Solid.makeCylinder(CAM["barrel"] / 2 + 0.5, 12, lens_c - d * 6, d))
    vis = vis.cut(lens_bevel())
    tx, ty = TOF_POS
    sens_front = Z_IN - 0.2
    grow = (D - sens_front + 0.5) * math.tan(math.radians(TOF["fov_half"]))
    vis = vis.cut(frustum(TOF["sens_w"] + 0.4, TOF["sens_h"] + 0.4, 0.6, sens_front,
                          TOF["sens_w"] + 0.4 + 2 * grow, TOF["sens_h"] + 0.4 + 2 * grow, 1.5, D + 0.5, tx, ty))
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

    # ToF
    tx, ty = TOF_POS
    sf = Z_IN - 0.2
    bf = sf - TOF["sens_t"]
    tof = box(tx - TOF["w"] / 2, tx + TOF["w"] / 2, ty - TOF["h"] / 2, ty + TOF["h"] / 2, bf - TOF["pcb"], bf)
    tof = tof.fuse(box(tx - TOF["sens_w"] / 2, tx + TOF["sens_w"] / 2, ty - TOF["sens_h"] / 2, ty + TOF["sens_h"] / 2, bf, sf))
    tof = tof.fuse(box(tx - 5, tx + 5, ty - TOF["h"] / 2 + 1, ty - TOF["h"] / 2 + 6, bf - TOF["pcb"] - TOF["back"], bf - TOF["pcb"]))
    tof = tof.fuse(box(tx - 5, tx + 5, ty + TOF["h"] / 2 - 6, ty + TOF["h"] / 2 - 1, bf - TOF["pcb"] - TOF["back"], bf - TOF["pcb"]))
    c["VL53L5CX ToF"] = tof
    c["_tof_sensor"] = box(tx - TOF["sens_w"] / 2, tx + TOF["sens_w"] / 2, ty - TOF["sens_h"] / 2, ty + TOF["sens_h"] / 2, bf, sf)
    c["_tof_board"] = tof.cut(c["_tof_sensor"])

    # USB 포트 위쪽 단 (USB2 = ly 2.4~15.6, USB3 = ly 20.4~33.6), 포트 입구 y = Pi 끝 + 2.1
    port_y = PI_Y0 + 87.1
    upper_z = PI_TOP + 11.5                               # 위쪽 포트 중심 높이

    # USB 마이크 동글 → USB 2.0 (부품표 지정), 위쪽 포트
    ux, _ = pi_world(0, 9.0)
    c["USB 마이크 동글"] = box(ux - UMIC["w"] / 2, ux + UMIC["w"] / 2, port_y, port_y + UMIC["len"],
                           upper_z - UMIC["t"] / 2, upper_z + UMIC["t"] / 2)
    # USB 스피커 플러그 → USB 3.0 (부품표 지정), 위쪽 포트. ㄱ자 플러그면 더 짧아진다
    sx, _ = pi_world(0, 27.0)
    c["USB 스피커 플러그"] = box(sx - 6.0, sx + 6.0, port_y, port_y + 20.0, upper_z - 4.0, upper_z + 4.0)
    # USB 스피커 사운드 보드 (케이스에서 꺼낸 것, 실측 후 USPK_BOARD 수정)
    b = USPK_BOARD
    c["USB 스피커 보드"] = box(b["x0"], b["x1"], b["y0"], b["y1"], b["z0"], b["z1"])

    # 스피커
    sx_, sy_ = SPEAKER["cx"], SPEAKER["cy"]
    spk = cyl(SPEAKER["dia"] / 2, Z_IN - 3.0, Z_IN, sx_, sy_)
    spk = spk.fuse(cyl(9.0, Z_IN - SPEAKER["depth"], Z_IN - 3.0, sx_, sy_))
    c["USB 스피커 유닛 ø28"] = spk

    # 버튼
    bx, by = BUTTON["cx"], BUTTON["cy"]
    btn = cyl(BTN["head"] / 2, D, D + BTN["head_t"], bx, by)
    btn = btn.fuse(cyl(BTN["body"] / 2 - 0.15, Z_IN - BTN["length"], D, bx, by))
    btn = btn.fuse(cyl(BTN["nut"] / 2, Z_IN - BTN["nut_t"], Z_IN, bx, by))
    c["16mm 호출벨"] = btn

    # LED (3 mm)
    lx, ly = LED_SLOT["cx"], LED_SLOT["cy"]
    c["상태 LED"] = box(lx - 2.5, lx + 2.5, ly - 2.5, ly + 2.5, Z_IN - 1.2 - 3.0, Z_IN - 1.2)
    return c


def build_all():
    parts = {
        "01_front_shell": build_shell(),
        "02_lcd_pi_chassis": build_frame(),
        "03_wall_plate": build_plate(),
        "04_black_visor": build_visor(),
        "05_led_light_pipe": build_light_pipe(),
    }
    return parts, components()
