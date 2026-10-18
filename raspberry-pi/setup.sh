#!/usr/bin/env bash
# Raspberry Pi 4 (Ubuntu 22.04) 단말 설치. 여러 번 실행해도 된다.
#   cd raspberry-pi && ./setup.sh
set -euo pipefail
cd "$(dirname "$0")"

echo "== 패키지 설치"
sudo apt-get update
sudo apt-get install -y i2c-tools alsa-utils python3-venv python3-rpi.gpio

echo "== I2C 활성화 확인"
CONFIG=/boot/firmware/config.txt
if ! grep -qE '^dtparam=i2c_arm=on' "$CONFIG"; then
    echo "dtparam=i2c_arm=on" | sudo tee -a "$CONFIG" >/dev/null
    echo "   $CONFIG 에 I2C를 켰습니다. 재부팅이 필요합니다."
    NEED_REBOOT=1
fi

echo "== 장치 권한 (I2C=dialout, 웹캠=video, 사운드=audio)"
# 이 Ubuntu 이미지는 /lib/udev/rules.d/99-gpio.rules 가 /dev/i2c-* 를 dialout 그룹에 준다.
MISSING=""
for g in dialout video audio; do
    id -nG "$USER" | tr ' ' '\n' | grep -qx "$g" || MISSING="$MISSING $g"
done
if [ -n "$MISSING" ]; then
    sudo usermod -aG "$(echo $MISSING | tr ' ' ',')" "$USER"
    echo "   그룹 추가:$MISSING  → 다시 로그인해야 적용됩니다."
    NEED_RELOGIN=1
fi

echo "== Python 가상환경"
# apt의 RPi.GPIO를 쓰기 위해 system-site-packages를 켠다.
[ -d .venv ] || python3 -m venv --system-site-packages .venv
.venv/bin/pip install -q -r requirements.txt

echo "== 장치 확인"
if sudo i2cdetect -y 1 | grep -q ' 29'; then echo "   VL53L0X: OK (0x29)"; else echo "   VL53L0X: 안 보임 — 배선 확인"; fi
if [ -e /dev/video0 ]; then echo "   웹캠: OK (/dev/video0)"; else echo "   웹캠: 없음"; fi
if sudo arecord -l 2>/dev/null | grep -q 'USB Audio'; then echo "   USB 마이크: OK"; else echo "   USB 마이크: 없음"; fi
if sudo aplay -l 2>/dev/null | grep -q 'Headphones'; then echo "   3.5mm 출력: OK"; else echo "   3.5mm 출력: 없음"; fi

echo
[ -n "${NEED_REBOOT:-}" ] && echo "※ 재부팅하세요: sudo reboot"
[ -n "${NEED_RELOGIN:-}" ] && [ -z "${NEED_REBOOT:-}" ] && echo "※ 다시 로그인한 뒤 실행하세요."
echo "실행: .venv/bin/python main.py --offline   (장치별 시험은 README 참고)"
