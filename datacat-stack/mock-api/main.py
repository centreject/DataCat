"""DataCat 목업 API — Spring Boot 가 완성되기 전까지 API 명세 v1.4 9·10장대로 응답한다.

앱 담당·Pi 담당이 서버 없이 먼저 붙여 보기 위한 것. 데이터는 메모리에만 있고,
시각은 요청할 때마다 '지금' 기준으로 다시 계산해서 항상 최근 기록처럼 보인다.

  GET  /api/v1/events?page=0&size=20     목록 (9.1)
  GET  /api/v1/events/{eventId}          상세 (9.2)
  GET  /api/v1/events/{eventId}/snapshot 스냅샷 (9.3) — 목업에는 사진이 없어 404
  GET  /api/v1/presets                   프리셋 (10.1)
  POST /api/v1/push-tokens               푸시 토큰 등록 (11.1) — 받기만 함
  GET  /health                           상태 확인
  POST /api/v1/_mock/visits              (시연용) 방금 새 방문이 온 것처럼 하나 추가

환경변수 MOCK_AUTO_VISIT_SECONDS (기본 180): 이 간격마다 새 방문이 저절로 하나씩 생긴다.
앱의 자동 새로고침(15초)과 "새 방문" 알림을 시연하기 위한 것. 0 이면 끈다.
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI
from fastapi.responses import JSONResponse

KST = timezone(timedelta(hours=9))
app = FastAPI(title="DataCat mock API", version="1.4-mock")


def _error(status: int, code: str, message: str) -> JSONResponse:
    # API 명세 12장 오류 형식
    return JSONResponse(status_code=status, content={"code": code, "message": message})


# (eventId, 몇 분 전 | (며칠 전, 시, 분), 머문 초, 필드들)
_SEED: list[tuple[int, object, int, dict]] = [
    (112, 4, 22, dict(triggerType="BUTTON", eventType="VISITOR_ACCEPTED", purpose="DELIVERY",
                      summary="치킨 배달 문 앞 보관", transcript="배민 주문하신 치킨 왔습니다. 문 앞에 두고 갈게요.",
                      mainCategory="배송", subCategory="음식 배달", responsePolicy="일반 접수",
                      reason="음식명(치킨)과 배달 앱 이름이 함께 언급됨")),
    (111, 52, 3, dict(triggerType="TOF", eventType="UNATTENDED_DELIVERY",
                      mainCategory="물품만 있음", subCategory="택배", responsePolicy="무응답",
                      reason="사람 없음 + 물품 감지 → 출력 없이 스냅샷만 기록")),
    (110, 135, 41, dict(triggerType="BUTTON", eventType="VISITOR_ACCEPTED", purpose="INSPECTION",
                        summary="가스 안전점검 재방문 예정",
                        transcript="안녕하세요, 도시가스 안전점검 나왔습니다. 안 계셔서 다음 주 화요일 오전에 다시 방문드릴게요.",
                        mainCategory="작업 방문", subCategory="검침·안전점검", responsePolicy="일반 접수",
                        reason="예약 여부를 확인할 수 없어 사용자 확인 필요", needsReview=True)),
    (109, 308, 9, dict(triggerType="TOF", eventType="VISITOR_TIMEOUT", transcript="",
                       mainCategory="기타·판단 불가", responsePolicy="무응답",
                       reason="안내 음성 출력 후 발화 없이 이탈")),
    (108, (1, 19, 40), 18, dict(triggerType="BUTTON", eventType="VISITOR_ACCEPTED", purpose="VISIT",
                                summary="친구 민지, 전화 요청", transcript="민지인데요, 연락이 안 돼서 와봤어. 이따 전화 줘!",
                                mainCategory="개인 방문", subCategory="지인", responsePolicy="일반 접수",
                                reason="이름과 함께 지인임을 밝힘")),
    (107, (1, 14, 12), 35, dict(triggerType="BUTTON", eventType="VISITOR_ACCEPTED", purpose="ETC",
                                summary="인터넷 통신사 변경 권유",
                                transcript="안녕하세요, 이번에 이 동 인터넷 바꾸시면 석 달 무료로 해드리고 있어서요. 전단지 꽂아두고 갈게요.",
                                mainCategory="영업·홍보 방문", subCategory="판매·영업", responsePolicy="일반 접수",
                                reason="통신사 변경·가입 권유 표현")),
    (106, (1, 11, 3), 2, dict(triggerType="TOF", eventType="UNATTENDED_DELIVERY",
                              mainCategory="물품만 있음", subCategory="택배", responsePolicy="무응답",
                              reason="사람 없음 + 물품 감지")),
    (105, (1, 9, 20), 5, dict(triggerType="TOF", status="FAILED", responsePolicy="장애 안내",
                              processingStatus="서버 장애",
                              reason="분석 서버 응답 시간 초과 — 기기가 오류 안내 후 세션을 닫음")),
    (104, (2, 21, 5), 27, dict(triggerType="BUTTON", eventType="VISITOR_ACCEPTED", purpose="DELIVERY",
                               summary="반품 상품 회수", transcript="반품 회수하러 왔습니다. 문 앞에 있는 박스 가져갈게요.",
                               mainCategory="수거", subCategory="반품·교환 수거", responsePolicy="일반 접수",
                               reason="반품·회수 표현")),
    (103, (2, 16, 30), 190, dict(triggerType="TOF", eventType="VISITOR_ACCEPTED", transcript="",
                                 mainCategory="안전 확인 필요", subCategory="장시간 체류", responsePolicy="일반 접수",
                                 reason="3분 넘게 머물렀지만 용건을 말하지 않음", needsReview=True)),
    (102, (2, 10, 15), 14, dict(triggerType="BUTTON", eventType="VISITOR_ACCEPTED", purpose="DELIVERY",
                                summary="호수 착오, 505호 배송", transcript="아 죄송합니다, 503호가 아니라 505호네요.",
                                mainCategory="잘못 방문", subCategory="주소 착오", responsePolicy="일반 접수",
                                reason="동·호수가 다르다고 말함")),
    (101, (3, 18, 2), 12, dict(triggerType="BUTTON", eventType="VISITOR_ACCEPTED", purpose="DELIVERY",
                               summary="택배 문 앞 보관", transcript="택배입니다. 문 앞에 놓고 갈게요.",
                               mainCategory="배송", subCategory="택배", responsePolicy="일반 접수",
                               reason="택배·문 앞 보관 표현")),
]


# ── 시연용 새 방문 ──────────────────────────────────────────
_ARRIVALS: list[dict] = [
    dict(triggerType="BUTTON", eventType="VISITOR_ACCEPTED", purpose="DELIVERY", summary="택배 문 앞 보관",
         transcript="CJ대한통운입니다. 택배 문 앞에 두고 갈게요.", mainCategory="배송", subCategory="택배",
         responsePolicy="일반 접수", reason="택배사 이름과 문 앞 보관 표현", _stay=19),
    dict(triggerType="TOF", eventType="UNATTENDED_DELIVERY", mainCategory="물품만 있음", subCategory="음식 배달",
         responsePolicy="무응답", reason="사람 없음 + 음식 봉투 감지", _stay=3),
    dict(triggerType="BUTTON", eventType="VISITOR_ACCEPTED", purpose="VISIT", summary="이웃 302호, 소음 문의",
         transcript="302호인데요, 저녁에 공사 소리가 나서 언제까지인지 여쭤보려고 왔어요.",
         mainCategory="개인 방문", subCategory="이웃", responsePolicy="일반 접수", reason="같은 동 주민임을 밝힘", _stay=24),
    dict(triggerType="BUTTON", eventType="VISITOR_ACCEPTED", purpose="INSPECTION", summary="아래층 누수, 긴급 점검 요청",
         transcript="관리사무소입니다. 아래층 천장에서 물이 새서 급하게 확인이 필요합니다. 연락 부탁드려요.",
         mainCategory="공공·긴급 방문", subCategory="긴급 상황", responsePolicy="긴급 알림",
         reason="누수와 긴급 확인 요청을 명확히 언급", needsReview=True, _stay=31),
]
_AUTO_SECONDS = int(os.environ.get("MOCK_AUTO_VISIT_SECONDS", "180"))
_extra: list[dict] = []
_next_id = 200
_next_auto = datetime.now(KST) + timedelta(seconds=_AUTO_SECONDS) if _AUTO_SECONDS > 0 else None


def _add_visit(at: datetime) -> dict:
    global _next_id
    tpl = dict(_ARRIVALS[(_next_id - 200) % len(_ARRIVALS)])
    stay = tpl.pop("_stay")
    at = at.replace(microsecond=0)
    e = {
        "eventId": _next_id, "deviceId": "door-01", "triggerType": "TOF", "eventType": None, "purpose": None,
        "summary": None, "transcript": None, "status": "COMPLETED", "snapshotUrl": None,
        "occurredAt": at.isoformat(), "endedAt": (at + timedelta(seconds=stay)).isoformat(), "needsReview": False,
    }
    e.update(tpl)
    _next_id += 1
    _extra.append(e)
    del _extra[:-50]  # 메모리에 최대 50건만
    return e


def _catch_up_auto_visits() -> None:
    """요청이 올 때 지나간 주기만큼 새 방문을 만들어 둔다 (별도 스레드 없이)."""
    global _next_auto
    if _next_auto is None:
        return
    now = datetime.now(KST)
    while _next_auto <= now:
        _add_visit(_next_auto)
        _next_auto += timedelta(seconds=_AUTO_SECONDS)


def _events() -> list[dict]:
    _catch_up_auto_visits()
    now = datetime.now(KST).replace(microsecond=0)
    out = [dict(e) for e in _extra]
    for event_id, when, stay, fields in _SEED:
        if isinstance(when, tuple):
            days, hour, minute = when
            at = (now - timedelta(days=days)).replace(hour=hour, minute=minute, second=0)
        else:
            at = now - timedelta(minutes=when)
        e = {
            "eventId": event_id,
            "deviceId": "door-01",
            "triggerType": "TOF",
            "eventType": None,
            "purpose": None,
            "summary": None,
            "transcript": None,
            "status": "COMPLETED",
            "snapshotUrl": None,  # 목업에는 사진이 없다 → 앱이 현관 그림으로 대신 그림
            "occurredAt": at.isoformat(),
            "endedAt": (at + timedelta(seconds=stay)).isoformat(),
            "needsReview": False,
        }
        e.update(fields)
        out.append(e)
    out.sort(key=lambda e: e["occurredAt"], reverse=True)
    return out


def _summary(e: dict) -> dict:
    # 목록 응답(9.1)에는 전사문을 넣지 않는다 — 상세에서만 내려준다
    return {k: v for k, v in e.items() if k not in ("transcript", "triggerType", "endedAt")}


@app.get("/api/v1/events")
def list_events(page: int = 0, size: int = 20):
    if page < 0 or not 1 <= size <= 100:
        return _error(400, "INVALID_REQUEST", "page 는 0 이상, size 는 1~100 이어야 합니다.")
    events = _events()
    return {
        "content": [_summary(e) for e in events[page * size:(page + 1) * size]],
        "page": page,
        "size": size,
        "totalElements": len(events),
    }


@app.get("/api/v1/events/{event_id}")
def get_event(event_id: int):
    for e in _events():
        if e["eventId"] == event_id:
            return e
    return _error(404, "NOT_FOUND", "기록을 찾을 수 없어요.")


@app.get("/api/v1/events/{event_id}/snapshot")
def get_snapshot(event_id: int):
    return _error(404, "NOT_FOUND", "목업 서버에는 스냅샷이 없어요.")


@app.get("/api/v1/presets")
def presets():
    return [
        {"presetId": 1, "type": "GREETING", "text": "마이크에 말씀해 주세요."},
        {"presetId": 2, "type": "COMPLETION", "text": "접수되었습니다. 추가 용건이 있으시면 벨을 다시 눌러주세요."},
        {"presetId": 3, "type": "FALLBACK", "text": "일시적인 오류로 접수할 수 없습니다. 잠시 후 다시 시도해 주세요."},
    ]


@app.post("/api/v1/push-tokens", status_code=201)
def register_push_token(body: dict):
    return {"registered": True, "platform": body.get("platform")}


@app.post("/api/v1/_mock/visits", status_code=201)
def mock_new_visit():
    return _add_visit(datetime.now(KST))


@app.get("/health")
def health():
    return {"status": "ok", "profile": "mock"}
