import struct
import subprocess
import unittest

from audio_input import FRAME_BYTES, FRAME_MS, detect_utterance, to_wav
from audio_output import AudioOutput

VOICE = b"\x01" * FRAME_BYTES
QUIET = b"\x00" * FRAME_BYTES


def frames(*runs):
    """frames(("v", 10), ("q", 30)) -> 음성 10프레임 뒤 무음 30프레임."""
    for kind, count in runs:
        yield from [VOICE if kind == "v" else QUIET] * count


def is_speech(frame):
    return frame == VOICE


class DetectUtteranceTests(unittest.TestCase):
    def test_ends_after_silence(self):
        pcm = detect_utterance(frames(("q", 5), ("v", 20), ("q", 100)), is_speech, silence_ms=810)
        silence = 810 // FRAME_MS
        # 시작 판단 구간(10) + 남은 음성 + 침묵 27프레임
        self.assertEqual(len(pcm) // FRAME_BYTES, 10 + (20 - 6) + silence)

    def test_short_pause_does_not_end(self):
        pcm = detect_utterance(frames(("v", 10), ("q", 10), ("v", 10), ("q", 100)), is_speech,
                               silence_ms=600)
        self.assertGreater(len(pcm) // FRAME_BYTES, 30)

    def test_no_speech_times_out(self):
        self.assertIsNone(detect_utterance(frames(("q", 1000)), is_speech, no_speech_timeout_s=3))

    def test_short_noise_is_not_speech(self):
        runs = [("v", 3), ("q", 20)] * 10
        self.assertIsNone(detect_utterance(frames(*runs), is_speech, no_speech_timeout_s=5))

    def test_long_speech_is_capped(self):
        pcm = detect_utterance(frames(("v", 2000)), is_speech, max_s=3)
        self.assertEqual(len(pcm) // FRAME_BYTES, 3000 // FRAME_MS)

    def test_wav_header(self):
        wav = to_wav(b"\x00\x00" * 16000)
        fields = struct.unpack("<4sI4s4sIHHIIHH4sI", wav[:44])
        self.assertEqual(fields[5:11], (1, 1, 16000, 32000, 2, 16))
        self.assertEqual(fields[12], 32000)


class AudioOutputTests(unittest.TestCase):
    def test_preset_maps_to_file_and_waits(self):
        calls = []

        def run(cmd, **kwargs):
            calls.append(cmd)
            return subprocess.CompletedProcess(cmd, 0)

        with self.subTest("파일 없음"):
            self.assertFalse(AudioOutput(sounds_dir="/nonexistent", run=run).play_preset(1))
            self.assertEqual(calls, [])
        with self.subTest("알 수 없는 presetId"):
            self.assertFalse(AudioOutput(run=run).play_preset(99))

    def test_device_error_is_false(self):
        def run(cmd, **kwargs):
            return subprocess.CompletedProcess(cmd, 1)
        self.assertFalse(AudioOutput(run=run).play_wav_bytes(b"x"))


if __name__ == "__main__":
    unittest.main()
