"""Spring 단말 API 클라이언트(명세 6장). 표준 라이브러리만 쓴다."""

import json
import urllib.error
import urllib.request
import uuid

TIMEOUT_S = 10  # 통합 시험 2차 제안값(Pi → Spring)


class ApiError(Exception):
    """서버 오류 응답 또는 연결 실패. status가 None이면 연결 실패다."""

    def __init__(self, status, code, message):
        super().__init__(f"{status or '연결 실패'} {code}: {message}")
        self.status = status
        self.code = code


def _multipart(parts):
    """parts: [(이름, 파일 이름 또는 None, Content-Type, bytes)]"""
    boundary = uuid.uuid4().hex
    body = b""
    for name, filename, content_type, data in parts:
        disposition = f'form-data; name="{name}"'
        if filename:
            disposition += f'; filename="{filename}"'
        body += (f"--{boundary}\r\nContent-Disposition: {disposition}\r\n"
                 f"Content-Type: {content_type}\r\n\r\n").encode() + data + b"\r\n"
    body += f"--{boundary}--\r\n".encode()
    return body, f"multipart/form-data; boundary={boundary}"


class SpringClient:
    def __init__(self, base_url, timeout=TIMEOUT_S, opener=urllib.request.urlopen):
        self.base_url = base_url.rstrip("/") + "/api/v1/device/events"
        self.timeout = timeout
        self.opener = opener

    def create_event(self, metadata, jpeg):
        body, content_type = _multipart([
            ("metadata", None, "application/json", json.dumps(metadata).encode()),
            ("image", "capture.jpg", "image/jpeg", jpeg),
        ])
        return self._post(self.base_url, body, content_type)

    def send_audio(self, event_id, wav):
        body, content_type = _multipart([("audio", "speech.wav", "audio/wav", wav)])
        return self._post(f"{self.base_url}/{event_id}/audio", body, content_type)

    def end_event(self, event_id, reason, ended_at):
        body = json.dumps({"reason": reason, "endedAt": ended_at}).encode()
        return self._post(f"{self.base_url}/{event_id}/end", body, "application/json")

    def _post(self, url, body, content_type):
        request = urllib.request.Request(url, data=body, method="POST",
                                         headers={"Content-Type": content_type})
        try:
            with self.opener(request, timeout=self.timeout) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:
            try:
                error = json.load(exc)
            except ValueError:
                error = {}
            raise ApiError(exc.code, error.get("code", "HTTP_ERROR"),
                           error.get("message", exc.reason)) from None
        except (urllib.error.URLError, OSError, ValueError) as exc:
            raise ApiError(None, "NETWORK_ERROR", str(exc)) from None
