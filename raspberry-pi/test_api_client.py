import io
import json
import unittest
import urllib.error

from api_client import ApiError, SpringClient


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def opener_returning(payload, requests):
    def opener(request, timeout):
        requests.append(request)
        return FakeResponse(json.dumps(payload).encode())
    return opener


class SpringClientTests(unittest.TestCase):
    def test_create_event_sends_json_metadata_and_jpeg(self):
        requests = []
        client = SpringClient("http://server:8080/", opener=opener_returning(
            {"eventId": 1, "action": "START_RECEPTION"}, requests))
        resp = client.create_event({"deviceId": "door-01", "triggerType": "TOF"}, b"\xff\xd8jpeg")

        self.assertEqual(resp["eventId"], 1)
        request = requests[0]
        self.assertEqual(request.full_url, "http://server:8080/api/v1/device/events")
        self.assertTrue(request.get_header("Content-type").startswith("multipart/form-data; boundary="))
        body = request.data
        self.assertIn(b'name="metadata"\r\nContent-Type: application/json', body)
        self.assertIn(b'"deviceId": "door-01"', body)
        self.assertIn(b'name="image"; filename="capture.jpg"\r\nContent-Type: image/jpeg', body)
        self.assertIn(b"\xff\xd8jpeg", body)

    def test_audio_and_end_paths(self):
        requests = []
        client = SpringClient("http://server:8080", opener=opener_returning({}, requests))
        client.send_audio(7, b"RIFF")
        client.end_event(7, "VISITOR_LEFT", "2026-10-18T17:00:00+09:00")
        self.assertEqual(requests[0].full_url, "http://server:8080/api/v1/device/events/7/audio")
        self.assertIn(b'name="audio"; filename="speech.wav"', requests[0].data)
        self.assertEqual(requests[1].full_url, "http://server:8080/api/v1/device/events/7/end")
        self.assertEqual(json.loads(requests[1].data)["reason"], "VISITOR_LEFT")

    def test_error_response_becomes_api_error(self):
        def opener(request, timeout):
            raise urllib.error.HTTPError(request.full_url, 503, "Service Unavailable", {},
                                         io.BytesIO(b'{"code":"MODEL_SERVER_UNAVAILABLE","message":"x"}'))
        with self.assertRaises(ApiError) as ctx:
            SpringClient("http://server", opener=opener).send_audio(1, b"")
        self.assertEqual((ctx.exception.status, ctx.exception.code), (503, "MODEL_SERVER_UNAVAILABLE"))

    def test_connection_failure_becomes_api_error(self):
        def opener(request, timeout):
            raise urllib.error.URLError("Connection refused")
        with self.assertRaises(ApiError) as ctx:
            SpringClient("http://server", opener=opener).end_event(1, "TIMEOUT", "t")
        self.assertIsNone(ctx.exception.status)


if __name__ == "__main__":
    unittest.main()
