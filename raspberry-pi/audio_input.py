#!/usr/bin/env python3
"""방문객 발화 녹음. VAD로 발화 끝을 감지해 WAV(16kHz, 16bit, mono)를 메모리로 반환한다.

- 녹음은 파일로 저장하지 않는다(Zero-Storage). 반환한 bytes를 그대로 서버로 보낸다.
- 발화 후 침묵이 SILENCE_MS 이어지면 끝낸다(명세 6.3: 700~1,000ms).
- 마이크를 연 뒤 NO_SPEECH_TIMEOUT_S 동안 발화가 없으면 None. 서버에 TIMEOUT으로 종료를 알린다.
- 명세에는 고정 녹음 제한이 없지만 모델이 앞 30초만 전사하므로 MAX_S에서 자른다.
"""

import argparse
import collections
import subprocess
import struct

RATE = 16000
FRAME_MS = 30
FRAME_BYTES = RATE * FRAME_MS // 1000 * 2
DEFAULT_DEVICE = "plughw:CARD=Device,DEV=0"  # USB 마이크
SILENCE_MS = 800
NO_SPEECH_TIMEOUT_S = 5.0
MAX_S = 30.0
START_WINDOW = 10   # 최근 300ms 중
START_VOICED = 6    # 180ms 이상 음성이면 발화 시작으로 본다(문 닫는 소리 같은 짧은 잡음 무시).
VAD_MODE = 2        # 0~3, 클수록 잡음을 음성으로 덜 판정


def detect_utterance(frames, is_speech, silence_ms=SILENCE_MS,
                     no_speech_timeout_s=NO_SPEECH_TIMEOUT_S, max_s=MAX_S):
    """30ms 프레임들에서 발화 구간 PCM을 찾는다. 발화가 없으면 None."""
    silence_frames = silence_ms // FRAME_MS
    wait_frames = int(no_speech_timeout_s * 1000 // FRAME_MS)
    max_frames = int(max_s * 1000 // FRAME_MS)
    recent = collections.deque(maxlen=START_WINDOW)  # 발화 시작 직전 소리도 담는다.
    speech = None
    quiet = 0
    for i, frame in enumerate(frames):
        voiced = is_speech(frame)
        if speech is None:
            recent.append((frame, voiced))
            if sum(v for _, v in recent) >= START_VOICED:
                speech = [f for f, _ in recent]
            elif i + 1 >= wait_frames:
                return None
            continue
        speech.append(frame)
        quiet = 0 if voiced else quiet + 1
        if quiet >= silence_frames or len(speech) >= max_frames:
            break
    return b"".join(speech) if speech else None


def to_wav(pcm, rate=RATE):
    header = struct.pack("<4sI4s4sIHHIIHH4sI", b"RIFF", 36 + len(pcm), b"WAVE", b"fmt ", 16,
                         1, 1, rate, rate * 2, 2, 16, b"data", len(pcm))
    return header + pcm


def record_utterance(device=DEFAULT_DEVICE, vad_mode=VAD_MODE, **kwargs):
    """마이크를 열어 발화 하나를 녹음한다. 반환 즉시 마이크는 닫혀 있다."""
    import webrtcvad
    vad = webrtcvad.Vad(vad_mode)
    proc = subprocess.Popen(
        ["arecord", "-q", "-D", device, "-f", "S16_LE", "-r", str(RATE), "-c", "1", "-t", "raw"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def frames():
        while True:
            frame = proc.stdout.read(FRAME_BYTES)
            if len(frame) < FRAME_BYTES:
                err = proc.stderr.read().decode(errors="replace").strip()
                raise OSError(f"마이크 입력이 끊겼습니다: {err or '원인 불명'}")
            yield frame

    try:
        pcm = detect_utterance(frames(), lambda f: vad.is_speech(f, RATE), **kwargs)
    finally:
        # 오류가 나도 마이크는 반드시 닫는다(명세 11장: 마이크 즉시 차단).
        proc.kill()
        proc.wait()
    return None if pcm is None else to_wav(pcm)


def main():
    parser = argparse.ArgumentParser(description="VAD 녹음 시험. 녹음 후 바로 재생하고 버린다.")
    parser.add_argument("--device", default=DEFAULT_DEVICE)
    parser.add_argument("--silence-ms", type=int, default=SILENCE_MS)
    parser.add_argument("--vad-mode", type=int, default=VAD_MODE, choices=range(4))
    parser.add_argument("--no-play", action="store_true", help="녹음 결과를 재생하지 않음")
    args = parser.parse_args()

    print(f"말씀하세요. ({NO_SPEECH_TIMEOUT_S:g}초 안에 시작, {args.silence_ms}ms 침묵이면 종료)",
          flush=True)
    try:
        wav = record_utterance(args.device, args.vad_mode, silence_ms=args.silence_ms)
    except OSError as exc:
        print(f"녹음 실패: {exc}")
        return 1
    if wav is None:
        print("발화 없음 (서버에는 TIMEOUT으로 종료)")
        return 0
    print(f"녹음 완료: {(len(wav) - 44) / (RATE * 2):.2f}초, {len(wav)} bytes", flush=True)
    if not args.no_play:
        from audio_output import AudioOutput
        AudioOutput().play_wav_bytes(wav)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
