"""FCM 푸시 발송 (API 명세 11장).

- 토큰은 /data/push-tokens.json 에 저장해서 컨테이너를 다시 띄워도 남는다.
- Firebase 서비스 계정 키(json)가 있으면 FCM HTTP v1 으로 보내고, 없으면 토큰만 받아 둔다.
- 실제 Spring 서버로 옮길 때도 같은 규칙(제목·본문, data, tag=event_{eventId})을 쓰면 앱은 그대로 동작한다.
  → datacat-stack/PUSH.md 의 "Spring 으로 옮기기" 참고
"""
from __future__ import annotations

import json
import logging
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

log = logging.getLogger("push")
KST = timezone(timedelta(hours=9))
SCOPE = "https://www.googleapis.com/auth/firebase.messaging"
PLATFORMS = {"ANDROID", "IOS", "WEB"}


def visit_message(event: dict) -> tuple[str, str]:
    """방문 기록 → (알림 제목, 본문). 앱의 분류 이름과 같은 말을 쓴다."""
    main = event.get("mainCategory") or "새 방문"
    sub = event.get("subCategory")
    policy = event.get("responsePolicy")
    summary = event.get("summary")
    if policy == "긴급 알림" or main in ("공공·긴급 방문", "안전 확인 필요"):
        title = f"긴급 · {sub or main}"
    elif main == "물품만 있음":
        title = f"물품 도착 · {sub}" if sub else "물품 도착"
    else:
        title = f"새 방문 · {main}"
    body = summary or event.get("reason") or "방문 기록을 확인해 주세요."
    if event.get("needsReview"):
        body += " (확인 필요)"
    return title, body


class PushSender:
    def __init__(self, credentials_file: str, store_file: str):
        self._store = Path(store_file)
        self._lock = threading.Lock()
        self._pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="fcm")
        self._tokens: dict[str, dict] = self._load()
        self.last_result: dict | None = None
        self.project_id: str | None = None
        self._creds = None
        self._session = None
        self.problem: str | None = None

        path = Path(credentials_file) if credentials_file else None
        if not path or not path.is_file():
            self.problem = f"서비스 계정 키가 없어요 ({credentials_file or '경로 미설정'}). 토큰만 저장해요."
            log.warning(self.problem)
            return
        try:
            from google.auth.transport.requests import AuthorizedSession
            from google.oauth2 import service_account

            self._creds = service_account.Credentials.from_service_account_file(str(path), scopes=[SCOPE])
            self.project_id = self._creds.project_id
            self._session = AuthorizedSession(self._creds)
            log.info("FCM 발송 준비 완료 (project=%s, 저장된 토큰 %d개)", self.project_id, len(self._tokens))
        except Exception as e:  # 키 형식 오류 등
            self.problem = f"서비스 계정 키를 읽지 못했어요: {e}"
            log.error(self.problem)

    # ── 토큰 ───────────────────────────────────────────────
    @property
    def enabled(self) -> bool:
        return self._session is not None

    def _load(self) -> dict[str, dict]:
        try:
            return json.loads(self._store.read_text("utf-8"))
        except FileNotFoundError:
            return {}
        except Exception as e:
            log.error("토큰 파일을 읽지 못했어요: %s", e)
            return {}

    def _save(self) -> None:
        try:
            self._store.parent.mkdir(parents=True, exist_ok=True)
            tmp = self._store.with_suffix(".tmp")
            tmp.write_text(json.dumps(self._tokens, ensure_ascii=False, indent=1), "utf-8")
            tmp.replace(self._store)
        except Exception as e:
            log.error("토큰 파일을 저장하지 못했어요: %s", e)

    def register(self, token: str, platform: str) -> None:
        now = datetime.now(KST).isoformat(timespec="seconds")
        with self._lock:
            old = self._tokens.get(token)
            self._tokens[token] = {"platform": platform, "createdAt": old["createdAt"] if old else now, "updatedAt": now}
            self._save()

    def remove(self, token: str) -> None:
        with self._lock:
            if self._tokens.pop(token, None) is not None:
                self._save()

    def token_count(self) -> int:
        return len(self._tokens)

    # ── 발송 ───────────────────────────────────────────────
    def notify_event(self, event: dict) -> None:
        """방문 기록 하나를 모든 등록 기기에 보낸다 (요청을 막지 않게 백그라운드에서)."""
        title, body = visit_message(event)
        self._pool.submit(self._send_all, str(event["eventId"]), title, body)

    def send_test(self, event_id: str, title: str, body: str) -> None:
        self._pool.submit(self._send_all, event_id, title, body)

    def _send_all(self, event_id: str, title: str, body: str) -> None:
        if not self.enabled:
            self.last_result = {"at": _now(), "eventId": event_id, "skipped": self.problem}
            return
        with self._lock:
            tokens = list(self._tokens)
        ok, failed = 0, []
        for token in tokens:
            err = self._send_one(token, event_id, title, body)
            if err is None:
                ok += 1
            else:
                failed.append(err)
        self.last_result = {"at": _now(), "eventId": event_id, "title": title, "sent": ok, "failed": failed}
        log.info("푸시 eventId=%s 보냄 %d / 실패 %d", event_id, ok, len(failed))

    def _send_one(self, token: str, event_id: str, title: str, body: str) -> str | None:
        tag = f"event_{event_id}"
        message = {
            "message": {
                "token": token,
                "notification": {"title": title, "body": body},
                # API 11.1: 앱은 data.eventId 로 상세를 다시 불러온다. FCM data 값은 모두 문자열.
                "data": {"type": "VISIT_EVENT", "eventId": event_id, "tag": tag},
                "android": {
                    "priority": "HIGH",
                    "collapse_key": tag,
                    # 같은 eventId 로 다시 보내면 알림을 새로 쌓지 않고 덮어쓴다 (세션 병합)
                    "notification": {"tag": tag},
                },
            }
        }
        url = f"https://fcm.googleapis.com/v1/projects/{self.project_id}/messages:send"
        try:
            res = self._session.post(url, json=message, timeout=10)
        except Exception as e:
            return f"{token[:12]}…: 네트워크 오류 {e}"
        if res.status_code == 200:
            return None
        try:
            status = res.json().get("error", {}).get("status", "")
            detail = res.json().get("error", {}).get("message", res.text[:200])
        except ValueError:
            status, detail = "", res.text[:200]
        # 앱을 지웠거나 토큰이 만료됨 → 더 보내지 않도록 지운다
        if res.status_code == 404 or status in ("NOT_FOUND", "UNREGISTERED") or "not a valid FCM registration token" in detail:
            self.remove(token)
            return f"{token[:12]}…: 만료된 토큰이라 지웠어요"
        return f"{token[:12]}…: HTTP {res.status_code} {status} {detail}"

    def status(self) -> dict:
        return {
            "enabled": self.enabled,
            "projectId": self.project_id,
            "problem": self.problem,
            "tokens": [
                {"token": f"{t[:12]}…{t[-6:]}", **info} for t, info in sorted(self._tokens.items(), key=lambda kv: kv[1]["updatedAt"], reverse=True)
            ],
            "lastResult": self.last_result,
        }


def _now() -> str:
    return datetime.now(KST).isoformat(timespec="seconds")


def from_env() -> PushSender:
    return PushSender(
        credentials_file=os.environ.get("FCM_CREDENTIALS_FILE", "/secrets/firebase-service-account.json"),
        store_file=os.environ.get("PUSH_TOKEN_FILE", "/data/push-tokens.json"),
    )
