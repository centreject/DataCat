"""응대 전체 흐름의 오류 재현. 센서·카메라·마이크·스피커는 쓰지 않는다."""

import json
import threading
import unittest
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace
from unittest.mock import Mock, call, patch

import main
from api_client import ApiError, SpringClient
from audio_output import AudioOutput

EVENT_ID = 41
ENDED_AT = "2026-11-26T14:00:00+09:00"
WAV = b"RIFF" + b"\0" * 100


def reception():
    return {"eventId": EVENT_ID, "status": "WAITING_AUDIO", "action": "START_RECEPTION",
            "preset": {"presetId": 1, "text": "마이크에 말씀해 주세요."}}


def completion():
    return {"eventId": EVENT_ID, "status": "COMPLETED", "action": "PLAY_PRESET",
            "preset": {"presetId": 2, "text": "접수되었습니다."}}


class SessionSafetyTests(unittest.TestCase):
    def setUp(self):
        self.sensor = SimpleNamespace(last_mm=250, read_cm=lambda: 25)
        self.server = Mock(spec=SpringClient)
        self.server.create_event.return_value = reception()
        self.server.send_audio.return_value = completion()
        self.out = Mock(spec=AudioOutput)
        self.out.play_preset.return_value = True
        self.out.play_wav_bytes.return_value = True
        for name, value in (("capture_jpeg", b"jpeg"), ("visitor_present", True),
                            ("record_utterance", WAV), ("now_iso", ENDED_AT)):
            patcher = patch.object(main, name, return_value=value)
            setattr(self, name, patcher.start())
            self.addCleanup(patcher.stop)
        patcher = patch.object(main, "log")
        self.log = patcher.start()
        self.addCleanup(patcher.stop)

    def run_session(self):
        main.run_session(self.sensor, 50, self.server, self.out)

    def test_greeting_finishes_before_recording_and_completion_follows_upload(self):
        order = []
        self.out.play_preset.side_effect = lambda preset: order.append(("preset", preset)) or True
        self.record_utterance.side_effect = lambda: order.append(("record", None)) or WAV
        self.server.send_audio.side_effect = lambda event_id, wav: (
            order.append(("audio", event_id)) or completion())
        self.run_session()
        self.assertEqual(order, [("preset", 1), ("record", None),
                                 ("audio", EVENT_ID), ("preset", 2)])
        self.server.end_event.assert_not_called()

    def test_failed_greeting_blocks_microphone_even_if_error_tone_plays(self):
        for tone_ok in (True, False):
            with self.subTest(tone_ok=tone_ok):
                self.out.play_preset.return_value = False
                self.out.play_wav_bytes.return_value = tone_ok
                self.out.reset_mock()
                self.server.reset_mock()
                self.run_session()
                self.record_utterance.assert_not_called()
                self.server.send_audio.assert_not_called()
                self.server.end_event.assert_called_once_with(EVENT_ID, "DEVICE_CANCELLED", ENDED_AT)
                self.out.play_wav_bytes.assert_called_once()

    def test_microphone_error_reports_device_cancelled_instead_of_no_speech(self):
        self.record_utterance.side_effect = OSError("microphone disconnected")
        self.run_session()
        self.server.end_event.assert_called_once_with(EVENT_ID, "DEVICE_CANCELLED", ENDED_AT)
        self.server.send_audio.assert_not_called()

    def test_no_speech_still_reports_timeout(self):
        self.record_utterance.return_value = None
        self.run_session()
        self.server.end_event.assert_called_once_with(EVENT_ID, "TIMEOUT", ENDED_AT)
        self.server.send_audio.assert_not_called()

    def test_visitor_left_before_greeting_does_not_record(self):
        self.visitor_present.return_value = False
        self.run_session()
        self.out.play_preset.assert_not_called()
        self.record_utterance.assert_not_called()
        self.server.end_event.assert_called_once_with(EVENT_ID, "VISITOR_LEFT", ENDED_AT)

    def test_silent_standby_does_not_open_microphone(self):
        self.server.create_event.return_value = {"eventId": EVENT_ID, "action": "SILENT_STANDBY"}
        self.run_session()
        self.out.play_preset.assert_not_called()
        self.record_utterance.assert_not_called()
        self.server.end_event.assert_not_called()

    def test_audio_409_ends_local_session_without_retry_or_completion_prompt(self):
        self.server.send_audio.side_effect = ApiError(409, "EVENT_STATE_CONFLICT", "expired")
        self.run_session()
        self.server.send_audio.assert_called_once_with(EVENT_ID, WAV)
        self.server.end_event.assert_not_called()
        self.assertEqual(self.out.play_preset.call_args_list, [call(1)])

    def test_other_audio_errors_keep_error_prompt(self):
        self.server.send_audio.side_effect = ApiError(503, "MODEL_SERVICE_UNAVAILABLE", "unavailable")
        self.run_session()
        self.assertEqual(self.out.play_preset.call_args_list, [call(1), call(3)])
        self.server.end_event.assert_not_called()

    def test_event_creation_failure_does_not_record_or_end_unknown_event(self):
        self.server.create_event.side_effect = ApiError(503, "SERVICE_UNAVAILABLE", "unavailable")
        self.run_session()
        self.record_utterance.assert_not_called()
        self.server.end_event.assert_not_called()
        self.out.play_preset.assert_called_once_with(3)

    def test_device_cancel_notification_failure_does_not_reopen_microphone(self):
        self.out.play_preset.return_value = False
        self.server.end_event.side_effect = ApiError(None, "NETWORK_ERROR", "offline")
        self.run_session()
        self.record_utterance.assert_not_called()
        self.server.end_event.assert_called_once_with(EVENT_ID, "DEVICE_CANCELLED", ENDED_AT)

    def test_failed_completion_prompt_does_not_overwrite_completed_result(self):
        self.out.play_preset.side_effect = [True, False]
        self.out.play_wav_bytes.return_value = False
        self.run_session()
        self.server.send_audio.assert_called_once_with(EVENT_ID, WAV)
        self.server.end_event.assert_not_called()


class SessionHttpTests(unittest.TestCase):
    """실제 HTTP와 SpringClient를 사용한다. 상대 서버는 시험용이며 Spring·DB는 아니다."""

    def setUp(self):
        self.requests = []
        requests = self.requests

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                body = self.rfile.read(int(self.headers["Content-Length"]))
                requests.append((self.path, body))
                if self.path.endswith("/events"):
                    status, payload = 201, reception()
                elif self.path.endswith("/audio"):
                    status, payload = 409, {"code": "EVENT_STATE_CONFLICT", "message": "expired"}
                else:
                    status, payload = 200, {"eventId": EVENT_ID, "action": "END_SESSION"}
                data = json.dumps(payload).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def log_message(self, *args):
                pass

        self.http = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.http.serve_forever,
                                       kwargs={"poll_interval": 0.01}, daemon=True)
        self.thread.start()
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({})).open
        self.client = SpringClient(f"http://127.0.0.1:{self.http.server_port}", opener=opener)

    def tearDown(self):
        self.http.shutdown()
        self.http.server_close()
        self.thread.join(timeout=2)

    def test_failed_greeting_sends_device_cancelled_over_http_without_audio(self):
        out = Mock(spec=AudioOutput)
        out.play_preset.return_value = False
        out.play_wav_bytes.return_value = True
        with patch.object(main, "capture_jpeg", return_value=b"jpeg"), \
                patch.object(main, "visitor_present", return_value=True), \
                patch.object(main, "record_utterance", return_value=WAV) as record, \
                patch.object(main, "log"):
            main.run_session(SimpleNamespace(last_mm=250, read_cm=lambda: 25), 50, self.client, out)
        record.assert_not_called()
        self.assertEqual([path for path, _ in self.requests],
                         ["/api/v1/device/events", f"/api/v1/device/events/{EVENT_ID}/end"])
        self.assertEqual(json.loads(self.requests[-1][1])["reason"], "DEVICE_CANCELLED")

    def test_http_409_does_not_retry_audio_or_send_end_again(self):
        out = Mock(spec=AudioOutput)
        out.play_preset.return_value = True
        with patch.object(main, "capture_jpeg", return_value=b"jpeg"), \
                patch.object(main, "visitor_present", return_value=True), \
                patch.object(main, "record_utterance", return_value=WAV), \
                patch.object(main, "log"):
            main.run_session(SimpleNamespace(last_mm=250, read_cm=lambda: 25), 50, self.client, out)
        self.assertEqual([path for path, _ in self.requests],
                         ["/api/v1/device/events", f"/api/v1/device/events/{EVENT_ID}/audio"])
        self.assertEqual(out.play_preset.call_args_list, [call(1)])


if __name__ == "__main__":
    unittest.main()
