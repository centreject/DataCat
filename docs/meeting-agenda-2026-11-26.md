# 2026-11-26 회의 안건 추가 요청 (타 파트 점검 항목)

PR #19(Flutter 앱·`datacat-stack`·기획서), PR #21(Raspberry Pi 새 부품), PR #23(Server CI) 병합 뒤 전체 코드·계약 점검(`main` `975a505` 기준)에서 확인된 항목입니다.

- **이 PR의 목적**: 타 파트 코드를 수정하지 않고, **오늘(11/26) 회의 안건에 아래 항목을 추가·논의**하기 위한 정리 문서입니다.
- **AI 모델 담당 항목**: 별도 PR([#24](https://github.com/centreject/DataCat/pull/24))로 코드·테스트 수정까지 반영했습니다.

---

## 1. 앱 · 기획서 (덕민)

### [P1] Spring v1.6.1 `"단말 확인 필요"` · 오류/무응답 표시 확인
- **위치**: `app/datacat_frontdoor/lib/data/category.dart` (L90–124), `app/datacat_frontdoor/lib/ui/event_detail_screen.dart` (L147–171, L252–262, L297–315)
- **현상**:
  - 11주차 Spring의 `DEVICE_CANCELLED`, 120초 자동 만료, `A0`+음성 503 실패는 `status=COMPLETED`, `eventType="VISITOR_TIMEOUT"`(물품 없을 때), `responsePolicy="장애 안내"`, `processingStatus="단말 확인 필요"`/`"이미지 판단 실패"`, `needsReview=true`로 저장됩니다.
  - 현재 앱은 `status == FAILED`일 때만 오류 화면을 띄우고 `eventType == "VISITOR_TIMEOUT"`이면 무조건 `"용건 없이 떠난 방문객"`, `"안내 음성이 나간 뒤 아무 말 없이 떠났어요."`, `"사람을 확인하고 안내 음성을 내보냈어요 → 말하기 전에 자리를 떠났어요"`로 표시합니다.
  - `A4`(`CAMERA_BLOCKED`), `A5`(`NO_VISITOR`), `VISITOR_LEFT`(`안내 전 이탈`)도 안내 음성을 내보냈다는 타임라인/설명이 출력됩니다.
- **회의 논의**: `responsePolicy == "장애 안내"` 및 `A4`·`A5`·`안내 전 이탈` 표시 분기 보완 일정 확인.

### [P2] 앱 상태 동기화 · 캐시 · 입력 검증 보완
- `models.dart` (L114–125) · `event_store.dart` (L197–208): `VisitEvent.==`가 5개 필드만 비교해 `EventStore.upsert()` 시 `WAITING_AUDIO`의 분류·`processingStatus`·`needsReview`·`snapshotUrl` 갱신이 누락될 수 있음.
- `snapshot_view.dart` (L30–35): `Image.network`가 URL 기준으로 캐시해 30초 병합으로 교체된 스냅샷이 갱신되지 않음.
- `api.dart` (L87–93, L129–135) · `settings_screen.dart` (L81–93): 공백 URL 입력 시 `"http://"`가 예외 없이 영구 저장됨; `snapshotUri()`가 `origin.path` 접두사를 보존하지 않음.
- `push_center.dart` (L135–149, L166–174): 앱 시작 시 오프라인 등으로 `backend.token()`이 실패하면 이후 서버 변경(`attach()`) 시 토큰을 다시 받지 않고 실패 상태가 유지됨.
- `settings_screen.dart` (L141–145): `IndexedStack` 안에서 `fetchPresets()` 실패 Future가 영구 캐시됨.
- `nginx.conf` (L7–13): `proxy_pass http://api:8080`의 기동 시점 IP 고정 캐시(`api` 컨테이너 재생성 시 502).
- `tool/prepare_android.dart` (L35–37): 릴리스 APK 전역 `usesCleartextTraffic="true"`(로컬망만 허용하는 `network_security_config.xml` 검토).

### [P2] 기획서 ↔ 현재 구현(`API_v1_6.md` v1.6.1 · `purposes.json`) 동기화
- `판정표.md`: 11주차 `DEVICE_CANCELLED`·120초 만료·`"단말 확인 필요"`·A0 동시 실패 결과 미반영, L58 A2(`사람 없음`)의 `personCount >= 2` 오기, L64(A3→A1 병합)와 L100/Spring 구현(새 이벤트) 불일치, L114 multipart `/end` 표기, 존재하지 않는 기획 11·13·14·17장 참조.
- `상황분류_종류와_조건.md`: 깨진 `images/00_overview.svg`~`10_unknown.svg` 링크 11건, 최종 우선순위표(`잘못 방문` 8위, `공공기관` 5위)와 본문/`purposes.json` 충돌, 누수·이전 거주자·쓰러진 사람·오배송 회수·무발화 이탈의 중복 분류 정리 필요.

---

## 2. Raspberry Pi (수연)

### [P1] `VL53L5CX` 센서 판정 · 타이밍 보완
- **위치**: `raspberry-pi/tof_sensor.py` (L17–21, L46–57, L90–99), `gate.py` (L5–26), `main.py` (L92, L133–152)
- **현상**:
  - 모든 정상 구역이 `< 30mm`(센서 가림)일 때 `valid`가 비어 `NO_TARGET_MM(8190)` → `120cm`로 변환되면서 측정 실패(`None`)가 아닌 빈 현관(`CLEAR`/`VISITOR_LEFT`)으로 오판됨(`VL53L0X` 및 `README.md:219`와 불일치).
  - `check_data_ready()==False`일 때 캐시된 `self.last_mm`을 그대로 반환해 3회 접근 디바운스와 5회 게이트(0.24초)가 같은 프레임을 중복 집계할 수 있음. 반대로 I2C 읽기가 ~0.37초 걸려 매번 새 프레임이 들어오면 `clear_samples=30`이 3초가 아닌 약 14초로 늘어남.
  - `run_session()`(촬영·녹음) 블로킹 직후 `last_at` 경과 시간이 `L5CX_STALE_S(2.0)`를 이미 초과한 상태라 복귀 첫 폴링이 `check_data_ready()==False`이면 정상 센서를 오류(`None`)로 처리할 위험이 있음.
- **회의 논의**: R1 실제 데이터 수집·재시험 전 수정 범위 확인.

### [P1] Docker `/proc/asound` 마스킹 및 `main.py` 명세 5.3 · `DEVICE_CANCELLED` 연계
- **위치**: `raspberry-pi/docker-compose.yml` (L8–20), `audio_output.py` (L20–37), `main.py` (L58–65, L96–105, L145–149)
- **현상**:
  - 비특권 Docker 컨테이너는 `/proc/asound`를 마스킹해 `usb_card_device()`가 항상 `None`을 반환(USB 스피커·마이크 자동 감지 실패).
  - 기존 `main.py`의 `play_preset()`이 재생 성공 여부를 확인하지 않아, 스피커·`aplay` 실패 시 안내 음성 없이 마이크가 열림(명세 5.3). 또한 `record_utterance()` `OSError` 시 Spring v1.6.1의 `DEVICE_CANCELLED` 종료를 보내지 않아 세션이 120초 방치됨.

### [P2] 스크립트 · LCD · 카메라 · 오디오 수명 관리
- `setup.sh` (L4, L37–41): `set -o pipefail` + `i2cdetect -y 1 | grep -q ' 29'` 조합에서 `SIGPIPE(141)`로 `0x29`가 정상 연결돼도 미감지로 출력될 수 있음. L39는 USB ID(`0c76:160a`) 대신 `'USB Audio'`를 검사해 스피커만 있어도 마이크 OK 오탐 가능.
- `lcd_eyes.py` (L18, L23–57, L80–88, L121–122): L1(`main.py` 통합) 전 import 시 하드웨어 초기화 분리, 종료 시 `s.close()`·백라이트 끄기·`G.cleanup()`, `time.monotonic()` 적용 필요. *(참고: `BL=GPIO18`이 `README.md:98`의 MAX98357A I2S `BCLK`와 겹치므로 추후 I2S 복구 시 핀 조정 필요.)*
- `camera.py` (L15–33) · `main.py` (L76, L147): CSI 활성화 시 USB 웹캠이 `/dev/video1+`로 밀리지만 `main.py`에 `--camera`/`--device`나 `DATACAT_CAMERA_DEVICE`가 없음. 잘못된 `DATACAT_CAMERA`의 `ValueError`가 첫 방문 시 미처리 예외로 프로세스를 종료시킴.
- `audio_input.py` (L22–23, L67–85) · `audio_output.py` (L36–37): `DEFAULT_DEVICE`가 import 시 1회 고정, `record_utterance()`의 파이프 미닫힘 및 타임아웃 없는 블로킹 읽기.
- `raspberry-pi/README.md` (L148, L189, L263): 구버전 `feature/image-upload` 404 안내 및 Docker 포트 `:18080` 표기 보완.

---

## 3. 공통 스택 · 서버 (`datacat-stack` · Server CI — 덕민 · 인태)

### [P1] Cloudflare Tunnel 공개 시 `mock-api` 보안 노출
- **위치**: `datacat-stack/mock-api/main.py` (L286–303), `datacat-stack/mock-api/push.py` (L171–180)
- **현상**: `--profile tunnel`로 외부 공개 시 무인증 `GET /api/v1/_mock/push`가 `projectId`·기기 토큰 일부·키 경로를 노출하고, `POST /api/v1/_mock/push-test`와 `/_mock/visits`로 등록된 전체 기기에 무제한 푸시 발송 가능.
- **회의 논의**: `/_mock/*` 차단 또는 간단 인증/스위치 적용 여부 결정.

### [P1] `datacat-stack` Compose 단일화 · `docker-compose.spring.yml` 정리
- **위치**: `datacat-stack/docker-compose.spring.yml` (L16–39), `datacat-stack/PUSH.md` (L140–158), `server/src/main/java/com/datacat/server/event/EventSampleData.java` (L32–51)
- **현상**:
  - `SPRING_PROFILES_ACTIVE=dev` 기본값으로 들어가는 `2026-10-05` 샘플 3건(`WAITING_AUDIO`)이 Spring 11주차 `SessionExpiryScheduler`에 의해 기동 5초 뒤 전부 `"단말 확인 필요"` 오류 이벤트로 만료됨.
  - `FCM_ENABLED=true` 누락(`PUSH.md:140-147` 포함)으로 Spring FCM이 꺼진 채 실행되며, 이미 존재하는 `server/Dockerfile` 대신 `dockerfile_inline`(root 실행, TCP 헬스체크, `TZ` 누락)으로 빌드됨.
- **회의 논의**: 실제 서버 실행 구성을 `docker-compose.server.yml`(포트 `18080`) 중심으로 단일화할지 정리 방향 합의.

### [P2] `mock-api` 안정성 · 계약 · 문서 정리 & [P3] Server CI 참고
- `mock-api/main.py` (L180–185, L204–207) · `push.py` (L171–180): `_events()`와 `PushSender.status()` 락 누락(동시 순회·수정 경쟁), Spring v1.6.1과의 계약 차이(토큰 201 응답 본문/길이/플랫폼, 비-`DELIVERY` `subCategory`, 누수 `PUBLIC_EMERGENCY` 분류), `pi-sim.ps1` 기본 포트(`8080` vs `18080`), `deploy.sh` 기본 비밀번호 즉시 기동, `datacat-stack/README.md`·`PUSH.md` 구버전 내용 갱신.
- `.github/workflows/server.yml` (L19–21, 인태): 전체 구성 이상 없음. 소폭 개선안으로 `concurrency.cancel-in-progress`를 `${{ github.event_name == 'pull_request' }}`로 제한해 `main` 푸시 검증 취소를 방지하는 방안 참고.

---

각 항목의 우선순위와 반영 시점(R1 실제 데이터 수집·통합 시험 전/후)을 오늘 11/26 회의에서 함께 확정 부탁드립니다.
