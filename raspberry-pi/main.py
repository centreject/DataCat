#!/usr/bin/env python3
"""현관 응대 흐름(명세 5장). 지금은 서버 없이 Pi 단독으로 실행한다(--offline).

ToF 접근 감지 → 사진 촬영 → 이벤트 생성 → START_RECEPTION이면 재확인 게이트
→ 안내 음성 재생(끝날 때까지 대기) → 마이크 개방, VAD 녹음 → 음성 전송
→ 완료 안내 재생 → 방문객이 떠나 CLEAR가 나올 때까지 다음 접근을 받지 않음
"""

import argparse
import datetime
import time

from api_client import ApiError, SpringClient
from audio_input import record_utterance
from audio_output import AudioOutput, tone_wav
from camera import capture_jpeg
from distance_sensor import POLL_INTERVAL, ProximityDetector
from gate import visitor_present
from tof_sensor import TOF_MAX_MM, TofSensor

DEVICE_ID = "door-01"
# 서버 오류·준비 중(503)일 때 재생하는 오류 안내. Spring 프리셋 목록의 3번과 같다.
FALLBACK_PRESET = {"presetId": 3, "text": "일시적인 오류로 접수할 수 없습니다. 잠시 후 다시 시도해 주세요."}


def log(msg):
    print(f"[{datetime.datetime.now():%H:%M:%S.%f}"[:-3] + f"] {msg}", flush=True)


def now_iso():
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


class OfflineServer:
    """Spring 대신 명세의 정상 응답을 흉내 낸다. 받은 녹음은 확인용으로 다시 들려준다."""

    def __init__(self, out):
        self.out = out
        self.next_id = 1

    def create_event(self, metadata, jpeg):
        event_id, self.next_id = self.next_id, self.next_id + 1
        log(f"  [서버 흉내] 이벤트 {event_id} 생성: {metadata}, 사진 {len(jpeg)} bytes")
        return {"eventId": event_id, "status": "WAITING_AUDIO", "action": "START_RECEPTION",
                "preset": {"presetId": 1, "text": "마이크에 말씀해 주세요."}}

    def send_audio(self, event_id, wav):
        log(f"  [서버 흉내] 이벤트 {event_id} 음성 수신 {len(wav)} bytes → 녹음 다시 듣기")
        self.out.play_wav_bytes(wav)
        return {"eventId": event_id, "status": "COMPLETED", "action": "PLAY_PRESET",
                "preset": {"presetId": 2, "text": "접수되었습니다."}}

    def end_event(self, event_id, reason, ended_at):
        log(f"  [서버 흉내] 이벤트 {event_id} 종료: {reason}")
        return {"eventId": event_id, "status": "COMPLETED", "action": "END_SESSION"}


def play_preset(out, preset):
    """프리셋 음원을 재생한다. 음원 파일이 아직 없으면 삐 소리로 대신한다."""
    preset_id = preset["presetId"]
    log(f"  안내 재생: presetId={preset_id} \"{preset.get('text', '')}\"")
    if not out.play_preset(preset_id):
        log(f"  (presetId={preset_id} 음원 파일 없음 → 삐 소리로 대체)")
        out.play_wav_bytes(tone_wav())


def end_session(server, event_id, reason):
    try:
        server.end_event(event_id, reason, now_iso())
    except ApiError as exc:
        log(f"  종료 알림 실패({reason}): {exc}")


def run_session(sensor, release_cm, server, out):
    distance_mm = sensor.last_mm
    jpeg = capture_jpeg()
    log(f"  사진 촬영 {len(jpeg)} bytes")
    try:
        resp = server.create_event({"deviceId": DEVICE_ID, "triggerType": "TOF",
                                    "distanceMm": distance_mm, "capturedAt": now_iso()}, jpeg)
    except ApiError as exc:
        log(f"  이벤트 생성 실패: {exc}")
        play_preset(out, FALLBACK_PRESET)
        return
    event_id = resp["eventId"]
    log(f"  이벤트 {event_id}: status={resp.get('status')} action={resp.get('action')}")
    if resp.get("action") != "START_RECEPTION":
        log("  응대 안 함")
        return

    # 명세 5.3: 안내 재생 직전 방문객이 아직 있는지 다시 확인한다.
    if not visitor_present(sensor.read_cm, release_cm):
        log("  재확인 게이트: 방문객 이탈 → 안내 생략")
        end_session(server, event_id, "VISITOR_LEFT")
        return
    play_preset(out, resp["preset"])

    # 안내가 끝난 뒤에만 마이크를 연다.
    log("  마이크 개방, 발화 대기")
    wav = record_utterance()
    log("  마이크 닫힘")
    if wav is None:
        log("  발화 없음")
        end_session(server, event_id, "TIMEOUT")
        return
    log(f"  녹음 {(len(wav) - 44) / 32000:.1f}초")
    try:
        resp = server.send_audio(event_id, wav)
    except ApiError as exc:
        log(f"  음성 전송 실패: {exc}")
        play_preset(out, FALLBACK_PRESET)
        return
    finally:
        del wav  # 녹음 원본은 남기지 않는다.
    if resp.get("action") == "PLAY_PRESET" and resp.get("preset"):
        play_preset(out, resp["preset"])


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--server", metavar="URL", help="Spring 주소(예: http://192.168.0.10:8080)")
    mode.add_argument("--offline", action="store_true", help="서버 없이 실행(서버 응답 흉내)")
    parser.add_argument("--threshold-cm", type=float, default=30)
    parser.add_argument("--release-cm", type=float, default=50)
    parser.add_argument("--samples", type=int, default=3)
    parser.add_argument("--clear-s", type=float, default=3.0)
    args = parser.parse_args()
    if not args.release_cm < TOF_MAX_MM / 10:
        parser.error(f"--release-cm은 {TOF_MAX_MM / 10:g}cm보다 작아야 합니다.")

    detector = ProximityDetector(args.threshold_cm, args.release_cm, args.samples,
                                 clear_samples=round(args.clear_s / POLL_INTERVAL))
    sensor = TofSensor()
    out = AudioOutput()
    server = OfflineServer(out) if args.offline else SpringClient(args.server)
    log(f"서버: {'없음(--offline)' if args.offline else args.server}")
    log(f"감시 시작:접근 <= {args.threshold_cm:g}cm / 해제 >= {args.release_cm:g}cm (종료: Ctrl+C)")
    try:
        while True:
            event = detector.update(sensor.read_cm())
            if event == "APPROACH":
                log(f"APPROACH {sensor.last_mm}mm → 응대 시작")
                try:
                    run_session(sensor, args.release_cm, server, out)
                except OSError as exc:
                    log(f"  장치 오류로 응대 중단: {exc}")
                log("응대 끝. 방문객이 떠날 때까지 대기")
            elif event == "CLEAR":
                log("CLEAR → 다음 방문객 감시")
            time.sleep(POLL_INTERVAL)
    except KeyboardInterrupt:
        log("종료")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
