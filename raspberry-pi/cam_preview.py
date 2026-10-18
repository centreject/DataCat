"""웹캠 실시간 미리보기. 브라우저에서 http://localhost:8090 으로 본다."""

import argparse
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import cv2

PAGE = b"""<!doctype html><meta charset="utf-8"><title>DataCat cam</title>
<body style="margin:0;background:#111;display:grid;place-items:center;height:100vh">
<img src="/stream" style="max-width:100%;max-height:100vh"></body>"""


class Camera:
    """캡처 스레드 하나가 최신 JPEG만 보관하고, 접속한 브라우저들이 그것을 나눠 쓴다."""

    def __init__(self, index, quality):
        self.cap = cv2.VideoCapture(index, cv2.CAP_V4L2)
        if not self.cap.isOpened():
            raise RuntimeError(f"/dev/video{index}를 열 수 없습니다 (video 그룹 권한 확인)")
        self.quality = quality
        self.jpeg = None
        self.cond = threading.Condition()
        threading.Thread(target=self._loop, daemon=True).start()

    def _loop(self):
        while True:
            ok, frame = self.cap.read()
            if not ok:
                time.sleep(0.1)
                continue
            ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, self.quality])
            if ok:
                with self.cond:
                    self.jpeg = buf.tobytes()
                    self.cond.notify_all()

    def next_frame(self):
        with self.cond:
            self.cond.wait(timeout=2)
            return self.jpeg


def make_handler(camera):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/":
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(PAGE)
            elif self.path == "/stream":
                self.send_response(200)
                self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
                self.send_header("Cache-Control", "no-cache")
                self.end_headers()
                try:
                    while True:
                        jpeg = camera.next_frame()
                        if jpeg is None:
                            continue
                        self.wfile.write(b"--frame\r\nContent-Type: image/jpeg\r\n"
                                         + f"Content-Length: {len(jpeg)}\r\n\r\n".encode()
                                         + jpeg + b"\r\n")
                except (BrokenPipeError, ConnectionResetError):
                    pass  # 브라우저 탭을 닫음
            else:
                self.send_error(404)

        def log_message(self, *args):
            pass

    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", type=int, default=0, help="/dev/videoN 번호 (기본: 0)")
    parser.add_argument("--port", type=int, default=8090)
    parser.add_argument("--host", default="127.0.0.1",
                        help="같은 네트워크의 다른 기기에서 보려면 0.0.0.0")
    parser.add_argument("--quality", type=int, default=80, help="JPEG 품질 (기본: 80)")
    args = parser.parse_args()

    camera = Camera(args.device, args.quality)
    server = ThreadingHTTPServer((args.host, args.port), make_handler(camera))
    server.daemon_threads = True
    print(f"미리보기: http://localhost:{args.port}  (종료: Ctrl+C)", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n종료")
    finally:
        camera.cap.release()


if __name__ == "__main__":
    main()
