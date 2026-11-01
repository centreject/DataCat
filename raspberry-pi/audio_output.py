#!/usr/bin/env python3
"""안내 음성 출력. ALSA aplay로 WAV를 재생하고 재생이 끝날 때까지 기다린다.

마이크는 안내 재생이 끝난 뒤에만 연다(명세 5.3). play_*가 반환된 시점이 재생 종료다.
출력 장치는 ALSA 장치 이름 하나로 정한다. 지금은 3.5mm 단자이고,
MAX98357A(I2S)로 바꾸면 그 카드 이름만 지정하면 된다.
"""

import argparse
import math
import struct
import subprocess
from pathlib import Path

# 카드 번호는 USB 연결 순서에 따라 바뀔 수 있어 카드 이름으로 지정한다.
DEFAULT_DEVICE = "plughw:CARD=Headphones,DEV=0"
SOUNDS_DIR = Path(__file__).with_name("sounds")
# 명세 10.2: presetId는 단말의 고정 음원 파일에 매핑된다.
PRESET_FILES = {
    1: "greeting.wav",    # GREETING: 마이크에 말씀해 주세요.
    2: "completion.wav",  # COMPLETION: 접수 완료
    3: "fallback.wav",    # FALLBACK: 오류 안내
}
PLAY_TIMEOUT_S = 30


class AudioOutput:
    def __init__(self, device=DEFAULT_DEVICE, sounds_dir=SOUNDS_DIR, run=subprocess.run):
        self.device = device
        self.sounds_dir = Path(sounds_dir)
        self.run = run

    def play_file(self, path):
        """재생에 성공하면 True. 파일이 없거나 장치 오류면 False."""
        if not Path(path).is_file():
            return False
        return self._aplay(["aplay", "-q", "-D", self.device, str(path)])

    def play_wav_bytes(self, wav):
        return self._aplay(["aplay", "-q", "-D", self.device, "-"], wav)

    def play_preset(self, preset_id):
        name = PRESET_FILES.get(preset_id)
        return name is not None and self.play_file(self.sounds_dir / name)

    def _aplay(self, cmd, stdin=None):
        try:
            result = self.run(cmd, input=stdin, timeout=PLAY_TIMEOUT_S,
                              stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        except (OSError, subprocess.TimeoutExpired):
            return False
        return result.returncode == 0


def tone_wav(freq=880, seconds=0.6, rate=16000, volume=0.3):
    """시험용 사인파 WAV(16bit mono)."""
    n = int(rate * seconds)
    pcm = b"".join(struct.pack("<h", int(32767 * volume * math.sin(2 * math.pi * freq * i / rate)))
                   for i in range(n))
    header = struct.pack("<4sI4s4sIHHIIHH4sI", b"RIFF", 36 + len(pcm), b"WAVE", b"fmt ", 16,
                         1, 1, rate, rate * 2, 2, 16, b"data", len(pcm))
    return header + pcm


def main():
    parser = argparse.ArgumentParser(description="안내 음성 출력 시험")
    parser.add_argument("target", nargs="?", help="WAV 파일 경로 또는 presetId(1~3). 생략하면 삐 소리")
    parser.add_argument("--device", default=DEFAULT_DEVICE)
    args = parser.parse_args()

    out = AudioOutput(args.device)
    if args.target is None:
        ok = out.play_wav_bytes(tone_wav())
    elif args.target.isdigit():
        ok = out.play_preset(int(args.target))
    else:
        ok = out.play_file(args.target)
    print("재생 완료" if ok else "재생 실패: 파일 또는 장치를 확인하세요.")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
