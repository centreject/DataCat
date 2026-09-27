from app.schemas import Detection
from tests.conftest import ready_client
from tests.fixtures.make_fixtures import noisy_jpeg, tiny_jpeg

URL = "/internal/v1/vision/detect"


class FakeVision:
    def __init__(self, detections):
        self.detections = detections
        self.seen = None

    def detect(self, image):
        self.seen = image
        return self.detections


def post_image(client, data: bytes):
    return client.post(URL, files={"image": ("x.jpg", data, "image/jpeg")})


def test_detect_route_returns_contract():
    fake = FakeVision([Detection(label="person", confidence=0.94)])
    with ready_client(vision=fake) as client:
        response = post_image(client, tiny_jpeg())
    assert response.status_code == 200
    assert response.json() == {"detections": [{"label": "person", "confidence": 0.94}]}
    assert fake.seen.mode == "RGB"


def test_detect_route_empty():
    with ready_client(vision=FakeVision([])) as client:
        response = post_image(client, tiny_jpeg())
    assert response.json() == {"detections": []}


def test_detect_route_rejects_non_jpeg():
    with ready_client(vision=FakeVision([])) as client:
        response = post_image(client, tiny_jpeg("PNG"))
    assert response.status_code == 400
    assert response.json()["code"] == "INVALID_IMAGE"


def test_detect_route_accepts_multi_megabyte_jpeg():
    # Camera Module 3 full-resolution JPEGs are several MB; Starlette's default part limit is 1 MB.
    data = noisy_jpeg(1600, 1200)
    assert len(data) > 2 * 1024 * 1024
    with ready_client(vision=FakeVision([])) as client:
        response = post_image(client, data)
    assert response.status_code == 200


def test_detect_route_rejects_upload_over_limit():
    with ready_client(vision=FakeVision([])) as client:
        response = post_image(client, b"\xff" * (17 * 1024 * 1024))
    assert response.status_code == 400
    assert response.json()["code"] == "INVALID_REQUEST"


def test_detect_route_missing_field():
    with ready_client(vision=FakeVision([])) as client:
        response = client.post(URL, data={})
    assert response.status_code == 400
    assert response.json()["code"] == "INVALID_REQUEST"
