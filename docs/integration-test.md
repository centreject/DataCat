# 통합 시험 기록

팀 전체 구성(앱 · 목업 API · Spring · 모델 서비스)을 한 PC에서 함께 띄워 확인한 기록. 최신 기록을 위에 쓴다.

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

- **프리셋 응답이 목업과 Spring에서 다름:** Spring은 명세 10.1대로 2건(GREETING, COMPLETION "접수되었습니다."), 목업 API는 3건(FALLBACK 추가, COMPLETION 문구가 더 김). 앱이 목업 기준으로 만들어지면 Spring으로 바꿀 때 어긋날 수 있다 → 덕민님·인태님 확인 필요(명세를 바꿀지, 목업을 맞출지).
- 목업 API의 `purpose`가 아직 옛 값(`INSPECTION`/`VISIT`/`ETC`) — 명세 v1.5 값으로 맞춰야 함(이미 요청 예정).
- 앱 컨테이너에 healthcheck가 없어 `Up`으로만 보인다(동작에는 문제 없음).
- 병합하면 hardware-design 파일(`README_RevH.md`, `models_RevC/`, 사진)이 루트에 놓인다 → `hardware/` 폴더로 모으는 것을 제안.

### 못 한 것 (다음 통합 시험에서)

- 방문객 → Pi → Spring → 모델 → DB → 앱 전체 흐름: Pi 코드가 없고, Spring에 이벤트·모델 호출 API가 아직 없다.
- 진짜 모델(GPU) 이미지로 같은 구성 — 모델 단독으로는 확인됨(`model-service/README.md`).
- 실제 Pi 녹음 파일 형식.
