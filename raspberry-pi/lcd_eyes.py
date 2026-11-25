#!/usr/bin/env python3
"""DataCat 단말 LCD 눈 애니메이션 (v2, 부드러운 시선 이동 + 깜빡임).

LCD: 3.5" 480x320, 컨트롤러 ST7796S, 4선 SPI, spidev로 직접 제어.
배선(BCM): DC=25(핀22), RST=27(핀13), BL=18(핀12), CS=CE0(핀24)
실행: sudo python3 lcd_eyes.py   (종료: Ctrl+C). 아직 main.py와 연결하지 않은 단독 실행용
필요 패키지: python3-spidev python3-rpi.gpio python3-pil python3-numpy
"""
import math
import random
import time

import numpy as np
import RPi.GPIO as G
import spidev
from PIL import Image, ImageDraw

DC, RST, BL = 25, 27, 18
W, H = 480, 320
Y0, Y1 = 50, 270          # 매 프레임 이 가로 띠만 다시 보냄 (전송량 약 1/3)
EYE_COLOR = (0, 220, 255)

G.setwarnings(False)
G.setmode(G.BCM)
for p in (DC, RST, BL):
    G.setup(p, G.OUT)
G.output(BL, 1)            # 백라이트 켜기 (BL이 GPIO18이라 코드로 켜야 함)

s = spidev.SpiDev()
s.open(0, 0)
s.max_speed_hz = 32_000_000   # 화면이 깨지면 16_000_000


def c(cmd, data=()):
    """명령 1바이트(DC=0) + 데이터(DC=1)."""
    G.output(DC, 0)
    s.writebytes([cmd])
    if data:
        G.output(DC, 1)
        s.writebytes(list(data))


# 초기화
G.output(RST, 0); time.sleep(0.1)
G.output(RST, 1); time.sleep(0.2)
c(0x11); time.sleep(0.2)   # 절전 해제
c(0x3A, [0x55])            # RGB565
c(0x36, [0x28])            # MADCTL: MV(가로 480x320) + BGR(패널이 BGR 순서)
c(0x29)                    # 화면 켜기

# 전체 검정으로 지우기
c(0x2A, [0, 0, (W - 1) >> 8, (W - 1) & 0xFF])
c(0x2B, [0, 0, (H - 1) >> 8, (H - 1) & 0xFF])
c(0x2C); G.output(DC, 1); s.writebytes2(bytes(W * H * 2))

# 이후 프레임은 Y0~Y1 띠에만 씀
c(0x2B, [0, Y0, (Y1 - 1) >> 8, (Y1 - 1) & 0xFF])

cx, cy, o = 0.0, 0.0, 1.0  # 시선 x, y(px), 눈 뜬 정도(0~1)


def to565(im):
    a = np.asarray(im, np.uint16)
    p = ((a[..., 0] >> 3) << 11) | ((a[..., 1] >> 2) << 5) | (a[..., 2] >> 3)
    return p.astype('>u2').tobytes()


def draw():
    im = Image.new('RGB', (W, Y1 - Y0))
    d = ImageDraw.Draw(im)
    for i, x in enumerate((130, 350)):
        w = 130 * (1 + 0.08 * cx / 55 * (1 if i else -1))   # 보는 쪽 눈이 약간 커짐
        h = max(150 * o, 6)
        X, Y = x + cx, 160 + cy - Y0
        d.rounded_rectangle((X - w / 2, Y - h / 2, X + w / 2, Y + h / 2),
                            min(30, h / 2), EYE_COLOR)
    c(0x2C); G.output(DC, 1); s.writebytes2(to565(im))


def anim(dur, f):
    """dur초 동안 ease-in-out(0~1) 값으로 f를 호출하며 그린다."""
    t0 = time.time()
    while True:
        t = min((time.time() - t0) / dur, 1)
        f(t * t * (3 - 2 * t))
        draw()
        if t >= 1:
            break


def look(x, y, dur=0.4):
    sx, sy = cx, cy

    def f(t):
        global cx, cy
        cx, cy = sx + (x - sx) * t, sy + (y - sy) * t
    anim(dur, f)


def blink():
    def f(t):
        global o
        o = abs(math.cos(t * math.pi))   # 1 -> 0 -> 1
    anim(0.3, f)


if __name__ == '__main__':
    try:
        draw()
        while True:
            time.sleep(random.uniform(0.8, 2.5))
            r = random.random()
            if r < 0.3:
                blink()
            elif r < 0.4:
                blink(); blink()
            else:
                look(random.uniform(-55, 55), random.uniform(-25, 25), random.uniform(0.3, 0.6))
            if random.random() < 0.3:
                look(0, 0, 0.4)
    except KeyboardInterrupt:
        pass
