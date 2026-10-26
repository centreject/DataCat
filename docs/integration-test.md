# 통합 시험 기록

팀 전체 구성(앱 · 목업 API · Spring · 모델 서비스)을 한 PC에서 함께 띄워 확인한 기록. 최신 기록을 위에 쓴다.

---

## 1차 통합(실기기) 때 AI 쪽 확인 항목 — 준비

Pi(실제 센서·웹캠·마이크) → Spring → 모델 → 앱. 수연님 3090 시험(10/18)에서 사진 단계까지는 동작을 확인했으니, 통합 날 아래를 순서대로 본다. 사진·녹음은 개인 공간이 담기므로 저장소에 올리지 않고 결과만 표로 적는다.

| # | 상황 | 기대 결과 | 전제 |
|---|---|---|---|
| 1 | 모델 준비 확인 | `/health`가 `ok`, 처음 실행이면 물품 가중치 자동 다운로드 | PR #7 병합 후 이미지 다시 빌드 |
| 2 | 사람이 문 앞에 섬 | `person` 감지 → `START_RECEPTION`, 접근부터 응대 지시까지 2초 안 | 카메라 정방향, 거리 센서와 같은 방향 |
| 3 | 택배 상자만 둠(사람 없음) | `package` 감지 → `SILENT_STANDBY` + 물품 알림 | 판정표 A3 |
| 4 | 택배를 둔 채 다시 센서 반응 | 같은 물품 알림이 다시 가지 않음 | 판정표 A-1 연결 후 |
| 5 | 렌즈를 손으로 가림 | `LOW_VISIBILITY` → 안전 확인 필요 | 판정표 A4 |
| 6 | 어두운 복도(조명 끔) | 사람이 있으면 여전히 응대하는지, 가림으로 잘못 보지 않는지 | 웹캠 노출 |
| 7 | 택배 기사 발화("택배 왔습니다, 문 앞에 둘게요") | `DELIVERY`/`PARCEL`, 요약 명사형, 음성 처리 1.5초 안 | 서버 `/audio` 구현 후 |
| 8 | 위협 발화("문 열어, 가만 안 둬") | `SAFETY_REVIEW`, 긴급 알림 | `/audio` 구현 후 |
| 9 | 말 없이 떠남 | `NO_SPEECH` 또는 `/end` → 판정표 B | `/end` 구현 후 |
| 10 | 모델 컨테이너를 멈춤 | 503 → Pi 오류 안내, 다시 켜면 복구 | — |

같은 기기의 30초 안 요청은 한 방문으로 합쳐지므로 경우를 바꿀 때는 30초 이상 쉰다.

---

## 2026-10-26 · 진짜 모델 + Spring 음성 접수·종료 (4차, PR #9)

Spring `feature/audio-session`(`44998f5`), 모델 `datacat-model`(lite, RTX 3060 Ti 8GB, GPU 6.5GB 사용), MySQL 8.4. 사람 사진으로 방문을 만든 뒤 평가용 합성 음성(`data/audio/tts`, 용건 9종 × 3)을 `/audio`로 보냈다.

| 항목 | 결과 |
|---|---|
| `gradlew test` | 통과 |
| 사진 → `/audio` → 조회 27건 | 음성까지 간 25건 중 용건 24건 일치, 모두 `PLAY_PRESET`(프리셋 2번). 2건은 사진에서 사람을 못 찾아 응대 없이 끝남(409) |
| `/audio` 처리 시간 | p50 1.25초 · p95 1.66초 (모델 단독 p95 1.70초 · 최대 2.11초) |
| 동시 2·4·8대 | 모두 200, 가장 늦은 응답 2.97 · 6.68 · 11.10초 |
| `/end` 음성 없이 (VISITOR_LEFT·TIMEOUT) | `END_SESSION`, 무응답 저장 |
| 음성 완료 뒤 늦은 `/end` | 결과 유지 |
| 종료된 방문에 `/audio` | 409 `EVENT_STATE_CONFLICT` |
| 같은 녹음 재전송 | 6ms, 재분석 없음 |
| 모델 정지 중 `/audio` → 재시작 후 재시도 | 503(2초) → 같은 방문으로 200 |

- 서버의 `DeviceEventService` 처리 메서드가 `synchronized`라 모든 기기 요청이 한 줄로 처리된다. 모델 호출이 겹치지 않으므로 서버의 음성 읽기 대기 5초로 충분하다(이전 10초 제안은 모델 쪽 요청이 겹치는 경우 기준). 기기가 많아지면 대기가 쌓여(8대 11.1초) Pi 대기 10초를 넘을 수 있다 → 여러 기기를 지원할 때 잠금 범위를 줄이고 읽기 대기를 10초로.
- AI 쪽 할 일: "쿠팡입니다. 문 앞에 두고 갑니다."의 배송 세부 유형이 `QUICK`(퀵 배송)으로 나옴(기대 `PARCEL`), 사람 사진 2장에서 사람 미검출. 물품 반복 알림(A-1) 실제 사진 시험은 30초 간격이 필요해 이번에는 하지 않았다.

---

## 2026-10-22 · 진짜 모델 + Spring 판정·푸시 (3차, PR #8)

Spring `feature/push-notification`(`3617170`), 모델 `datacat-model`(파인튜닝 + 상용 점검 반영, lite), MySQL 8.4. 2차와 같은 사진 50장에 더해, 사진마다 새 기기로 보내고 `GET /api/v1/events/{id}`의 앱 표시 필드를 확인했다.

| 항목 | 결과 |
|---|---|
| `gradlew test` | 통과 |
| 사진 50장 응대 지시 | 50/50, Spring p95 176ms(모델 단독 76ms) |
| 8대 동시 | 8/8, 최대 0.81초 |
| 사람 → A1 | `START_RECEPTION`, 분류는 음성 뒤, 여러 명 사진은 "복수 방문자" |
| 상자·봉지 → A3 | `UNATTENDED_DELIVERY` / 물품만 있음 / 무응답 |
| 빈 복도·동물 → A5 | `NO_VISITOR` / 기타·판단 불가 (빈 복도 1장은 모델 오탐으로 A3) |
| 회색 사진(렌즈 가림) → A4 | `CAMERA_BLOCKED` / 안전 확인 필요 / needsReview true |
| 모델 정지·로딩 중 → A0 | `START_RECEPTION`(정지 시 2.0초), 다시 켜면 정상 |

물품 반복 알림 방지(A-1)와 `/audio`·`/end`는 PR #8 범위 밖이라 시험하지 않았다.

---

## 2026-10-17 · 진짜 모델 + Spring 사진 접수 (2차)

Spring은 인태님 `feature/image-upload`(PR #5, `9a71dbd`), 모델은 진짜 이미지(`datacat-model`, `MODEL_PROFILE=lite`, RTX 3060 Ti 8GB), DB는 MySQL 8.4 컨테이너. 셋을 한 Docker 네트워크에 두고 Spring에 `MODEL_SERVICE_URL=http://<모델 컨테이너>:8000`만 주었다. 사진은 평가용 실제 사진 50장(사람·택배 상자·비닐봉투·빈 복도·동물 각 10장, 평균 292KB)을 `POST /api/v1/device/events`로 보냈다(명세 6.1 형식, 요청마다 다른 deviceId).

### 결과 — 모두 통과

| # | 확인 | 결과 |
|---|---|---|
| 1 | 모델이 켜지는 중에 사진 접수 | 503 `MODEL_SERVICE_UNAVAILABLE`, 0.4초 만에 응답 |
| 2 | 모델 준비 시간 | 첫 실행 292초(Docker Desktop을 막 켠 직후, 아래 참고) · 재시작 29초 · 다시 잰 새 컨테이너 22~28초 |
| 3 | 준비 직후 첫 요청 | 201 `START_RECEPTION`, 1.6초 |
| 4 | 50장 하나씩 — Spring 전체 처리 시간 | 중앙값 94ms · p95 151ms · 최대 249ms (모델만 46·70·109ms, Spring·DB·파일 저장 약 48ms) |
| 5 | 응대 지시 | 50/50 맞음 — 사람 사진은 `START_RECEPTION`, 나머지는 `SILENT_STANDBY` |
| 6 | 기기 4대 동시 | 4/4 성공, 최대 0.43초 |
| 7 | 기기 8대 동시 | 8/8 성공, 최대 0.81초 |
| 8 | 가장 큰 사진(819KB) | 0.12초 |
| 9 | 모델 중단 중 사진 접수 | 503 `MODEL_SERVICE_UNAVAILABLE`, 2.1초(연결 시도 제한 2초) |
| 10 | 모델 재시작 후 | 201로 바로 복구 |

GPU 메모리: 세 모델(이미지·음성·언어)을 다 올린 상태에서 6.7GB / 8GB.

### 타임아웃 제안

- **Spring → 모델(사진):** 지금 값(연결 2초, 응답 5초)으로 충분하다. 가장 나쁜 경우(8대 동시)도 0.8초라 여유가 6배 이상이다.
- **Spring → 모델(음성, 2단계):** 모델 혼자 p95 1.5초(10-04 측정, 음성 최대 30초)라 응답 10초를 제안한다.
- **Pi → Spring(사진):** Spring이 모델을 기다리는 최대 7초(2+5)보다 길어야 503을 받을 수 있다 → 10초.
- **모델 준비 중 503:** 켜진 직후 수 분간은 503이 정상이다. Pi는 503이면 오류 안내(프리셋 3)를 재생하고, compose에서는 Spring이 모델 healthcheck를 기다리게 한다(`model-service/README.md`의 compose 예시).

### 발견한 것

- 모델 중단 때 Spring 로그에 `ResourceAccessException` 전체 스택이 ERROR로 찍힌다. 응답은 의도대로(503)라 동작 문제는 없고, 로그만 한 줄 경고로 줄이면 읽기 쉽다.
- 첫 실행 준비 292초는 Docker Desktop을 막 켠 직후의 한 번뿐이었다. 다시 잰 값(새 컨테이너, 디스크 캐시를 비워도)은 22~28초: 라이브러리 3초 · 이미지 6초 · 음성 4초 · 언어 10초. 통합 당일에는 Docker Desktop을 켠 뒤 모델을 먼저 띄워 둔다.

### 못 한 것

- 실제 Pi에서 보낸 사진(Pi 사진 전송 개발 후), 음성 경로(2단계), RTX 3090 `full` 프로필.

---

## 2026-10-05 · 브랜치 합친 상태로 함께 띄우기 (1차)

**목적:** 각 파트 브랜치를 main에 합쳤을 때 충돌 없이 모두 함께 뜨는지, 서비스끼리 compose 이름으로 통하는지 확인한다. 데이터가 파트 사이를 실제로 흐르는 시험은 아직 불가능하다(아래 "못 한 것").

**대상:** 임시 작업 폴더에서 `main 578896c+ccafdfc` + `feature/ai-model 14ef3f4` + `feature/app-design 5adb0f0` + `feature/hardware-design 62eec39`을 차례로 병합(충돌 0). GitHub과 각 브랜치는 바꾸지 않았다.

**환경:** Windows 11 + WSL2 Ubuntu 22.04, Docker 29.8 / Compose 5.5, GPU 없이(모델은 가짜 서버).

**실행:** 덕민님 `datacat-stack/docker-compose.yml`은 그대로 두고, 모델 블록만 아래 파일로 덧붙였다. Spring은 아직 compose에 없어 `eclipse-temurin:21-jdk` 컨테이너로 같은 네트워크에 붙였다.

```yaml
# it-override.yml — docker compose -f docker-compose.yml -f it-override.yml up -d --build
services:
  model:
    build:
      context: ../model-service
      dockerfile: Dockerfile.mock
    ports:
      - "8000:8000"
```

### 결과 — 모두 통과

| # | 확인 | 결과 |
|---|---|---|
| 1 | 병합 충돌 | 없음 (ai-model → app-design → hardware-design 순) |
| 2 | 컨테이너 상태 | api `healthy`, model `healthy`, app `Up` (app은 healthcheck 없음). 전체 빌드·기동 약 3분 |
| 3 | 앱 화면 `GET :8081/` | 200 |
| 4 | 앱 → 목업 API 프록시 `GET :8081/api/v1/events`, `/api/v1/presets` | 200, 200 |
| 5 | 목업 API `GET :8080/health`, `/api/v1/events` | ok, 기록 12건 |
| 6 | 모델 `docker/smoke.py` (엔드포인트 4개 + 오류 형식) | 5/5 PASS |
| 7 | 컨테이너끼리 이름으로: api → `model:8000`, app → `api:8080`, app → `model:8000` | 모두 `ok` |
| 8 | Spring(main `server/`) `GET /api/v1/presets` | 200, 명세 10.1과 같음(2건) |
| 9 | Spring 컨테이너 → `model:8000/health` | `ok` — Spring이 쓸 주소 `http://model:8000`이 통함 |
| 10 | 모델 가짜 서버 시나리오 (`delivery.wav` / `emergency.wav` / `silent.wav` / `person_package.jpg`) | DELIVERY·PARCEL / PUBLIC_EMERGENCY / UNKNOWN+NO_SPEECH / person+package |
| 11 | 명세와 다른 음성 형식(48kHz 스테레오) | 400 `INVALID_AUDIO` (의도대로 거부) |

이미지 크기: app 131MB · 목업 API 223MB · 모델 가짜 서버 366MB (진짜 모델 이미지 12.3GB).

### 발견한 것

- **프리셋 응답이 목업과 Spring에서 다름:** Spring은 명세 10.1대로 2건(GREETING, COMPLETION "접수되었습니다."), 목업 API는 3건(FALLBACK 추가, COMPLETION 문구가 더 김). 앱이 목업 기준으로 만들어지면 Spring으로 바꿀 때 어긋날 수 있다 → **10-08 회의: 오류 안내를 포함한 3건으로 통일, Spring에 반영 예정(인태님).**
- 목업 API의 `purpose`가 아직 옛 값(`INSPECTION`/`VISIT`/`ETC`) — 명세 v1.5 값으로 맞춰야 함(이미 요청 예정).
- 앱 컨테이너에 healthcheck가 없어 `Up`으로만 보인다(동작에는 문제 없음).
- 병합하면 hardware-design 파일(`README_RevH.md`, `models_RevC/`, 사진)이 루트에 놓인다 → `hardware/` 폴더로 모으는 것을 제안.

### 못 한 것 (다음 통합 시험에서)

- 방문객 → Pi → Spring → 모델 → DB → 앱 전체 흐름: Pi 코드가 없고, Spring에 이벤트·모델 호출 API가 아직 없다.
- 진짜 모델(GPU) 이미지로 같은 구성 — 모델 단독으로는 확인됨(`model-service/README.md`).
- 실제 Pi 녹음 파일 형식.
