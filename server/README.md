# DataCat Spring 서버

Java 21 · Spring Boot 4.1.1 · Gradle Wrapper · MySQL

팀플 8주차 구현과 2026-10-24~25 로컬 검증을 반영한 문서다.
음성·종료 API를 구현했고, 수정 Android 앱에서 배송 결과 알림 수신과 22번 방문 상세·사진·전사문 표시를 확인했다.
10/26 모델 담당자가 PR #9의 실제 모델 시험 결과를 보고했다. 실제 Pi 마이크·스피커와 Docker 재현은 별도로 진행한다.
9주차의 리뷰 반영·대기 시간·실기 시험 계획은 [9주차 실행 계획](docs/week9-plan.md)을 따른다.

## 현재 구현 범위

| Method | URL | 기능 |
|---|---|---|
| POST | /api/v1/device/events | 메타데이터·JPEG 접수, Vision 호출, 사진 판정·병합 |
| POST | /api/v1/device/events/{eventId}/audio | WAV 접수, 음성 일괄 분석, 같은 방문 결과 갱신 |
| POST | /api/v1/device/events/{eventId}/end | JSON으로 이탈·무발화 종료 알림 |
| GET | /api/v1/events?page=0&size=20 | 방문 목록, 최신 발생순 페이지 조회 |
| GET | /api/v1/events/{eventId} | 방문 상세 조회 |
| GET | /api/v1/events/{eventId}/snapshot | 저장된 JPEG 조회 |
| GET | /api/v1/presets | 고정 프리셋 3종 조회 |
| POST | /api/v1/push-tokens | Android FCM 토큰 등록·재등록 |

2차 사진의 `POST /api/v1/device/events/{eventId}/snapshot`은 아직 구현하지 않았다.
현재 `/end`는 `application/json`만 받으며 선택 사진을 포함한 multipart는 지원하지 않는다.
상세 요청·응답 계약은 [API 명세 v1.5](../API_v1_5.md)를 따른다.

## 로컬 실행

1. 저장소를 내려받고 IntelliJ에서 `server/build.gradle`을 프로젝트로 연다.
2. Gradle JVM을 JDK 21로 지정하고 동기화한다.
3. 로컬 MySQL을 실행하고 아래 SQL로 DB를 생성한다.
4. ServerApplication 실행 설정에 DB 환경변수를 지정한다.
5. 샘플이 필요하면 Active profiles에 `dev`를 입력한다.
6. `com.datacat.server.ServerApplication`을 실행한다. 기본 포트는 8080이다.

```sql
CREATE DATABASE IF NOT EXISTS datacat
    CHARACTER SET utf8mb4;
```

| 환경변수 | 기본값·설정 | 역할 |
|---|---|---|
| DB_USERNAME | 필수: 본인의 MySQL 사용자 | DB 사용자 |
| DB_PASSWORD | 필수: 본인의 MySQL 비밀번호 | DB 비밀번호 |
| DB_URL | jdbc:mysql://localhost:3306/datacat | DB 접속 주소 |
| MODEL_SERVICE_URL | http://localhost:8000 | 모델 서비스 루트 주소 |
| MODEL_AUDIO_READ_TIMEOUT_MS | 5000 | 음성 모델 응답 읽기 대기(ms), 양수만 허용. 실측 비교 시 10000으로 변경 가능 |
| SNAPSHOT_DIR | ./data/snapshots | 사진 저장 폴더 |
| FCM_ENABLED | false | Firebase 푸시 활성화 |
| FCM_CREDENTIALS_FILE | 빈 값 | 활성화 시 서버용 서비스 계정 JSON 경로 |

- `MODEL_SERVICE_URL`에 `/internal/v1`을 붙이지 않는다.
- 상대 사진 경로는 Spring 프로세스 실행 폴더 기준이다. IntelliJ 작업 폴더가 `server`면 `server/data/snapshots`다.
- 서비스 계정 파일은 저장소 밖에 둔다. 예: `C:\springproject\datacat-secrets\firebase-service-account.json`.
- 비밀번호·키 원문은 코드나 문서에 적지 않는다.
- IntelliJ 환경변수는 해당 실행 설정에 적용된다. 별도 PowerShell에는 자동으로 전달되지 않는다.
- 현재 `spring.jpa.hibernate.ddl-auto=update`는 개발용이다.

서버 시작에는 MySQL이 필요하다. 프리셋·조회에는 실행 중인 모델이 필요하지 않다.
사진 모델 장애는 A0로 음성 접수를 시작한다. 음성 모델 장애의 상태 처리는 아래 표를 따른다.

`dev` 샘플은 events 테이블이 비어 있을 때만 3건 생성한다.
기존 데이터가 있으면 생성하지 않으며, 재시작·프로필 변경으로 기존 기록을 삭제하지 않는다.

## 모의 모델 실행

Docker Desktop의 엔진이 실행 중인지 확인한다. 아래 빌드는 저장소 루트에서 실행한다.

```powershell
docker build -f model-service/Dockerfile.mock -t datacat-model-mock model-service
```

컨테이너를 처음 만드는 경우:

```powershell
docker run -d --name datacat-model-mock -p 8000:8000 datacat-model-mock
```

이미 같은 이름의 컨테이너가 있으면 새로 만들지 않고 시작한다.

```powershell
docker start datacat-model-mock
curl.exe -i "http://localhost:8000/health"
```

예상 응답은 200과 `{"status":"ok","profile":"mock"}`다.
모의 모델은 파일 이름으로 결과를 선택한다. 같은 사진을 `person.jpg`와 `package.jpg`로 보내면 다른 가짜 결과를 받을 수 있다.
이는 통신·분류·저장 시험용이며 실제 인식 정확도 시험이 아니다.
현재 브랜치 전체의 Docker 구성 재현·GPU 모델 연결은 팀 통합 시험에서 확인한다.

## 사진 접수와 물품 상태

`POST /api/v1/device/events`는 multipart 두 파트를 받는다.

| 파트 | Content-Type | 내용 |
|---|---|---|
| metadata | application/json | deviceId, triggerType, capturedAt, 선택 distanceMm |
| image | image/jpeg | 읽을 수 있는 JPEG 파일 |

```json
{
  "deviceId": "door-01",
  "triggerType": "BUTTON",
  "distanceMm": 1850,
  "capturedAt": "2026-10-25T00:40:00+09:00"
}
```

- `deviceId`: 비어 있지 않은 100자 이하 문자열.
- `triggerType`: TOF 또는 BUTTON.
- `capturedAt`: 시간대를 포함한 ISO-8601. distanceMm은 생략 가능하며 제공하면 0 이상이다.
- JPEG 최대 16MB·40MP, 전체 multipart 요청 최대 17MB.
- distanceMm은 기록용이다. 안내 직전 이탈 재확인은 Pi가 로컬 센서로 한다.
- 신규 방문은 201, 기존 방문 재사용은 200을 반환한다.

사진 A0~A5를 판정하고 같은 기기의 최근 사진 요청을 30초 기준으로 병합한다.
진행 중인 음성 접수에 물품 사진이 추가돼도 음성 대기를 끝내지 않는다.
물품만 남은 완료 기록 뒤 새 사람·벨 응대는 새 방문으로 분리한다.

잔류 물품은 개수 비교 대신 있음/없음으로 관리한다.
같은 물품이 계속 있으면 30초 이후에도 기존 방문을 반환하고 추가 알림을 보내지 않는다.
유효한 A5 미감지 한 번은 상태 유지, 연속 두 번은 물품 상태만 해제한다.
과거 방문·사진은 남기며, 이후 물품이 다시 감지되면 새 방문을 만든다.
세션 중 물품이 한 번이라도 감지됐으면 `packageSeen=true`를 보존해 종료 판정에도 사용한다.

자세한 정책과 DB 호환은 [물품 상태 구현](docs/package-state-integration.md)을 따른다.

## 음성 접수와 종료

`POST /api/v1/device/events/{eventId}/audio`에 multipart `audio`를 전송한다.
파트 형식은 `audio/wav`, 파일은 PCM 16-bit·16kHz·mono이며 최대 16MB다.
모델은 앞 30초를 사용한다. Spring은 크기를 확인하고 내부 WAV 형식 검사는 모델에 맡긴다.

Spring은 `/internal/v1/audio/process`를 호출해 전사문·용건·배송 세부 유형·요약을 받는다.
판정표 C와 앱 표시 필드 6개를 같은 방문에 저장하고 다음 응답을 반환한다.

```json
{
  "eventId": 101,
  "status": "COMPLETED",
  "action": "PLAY_PRESET",
  "preset": {
    "presetId": 2,
    "text": "접수되었습니다."
  }
}
```

101은 예시다. 실제 요청에는 사진 접수에서 반환된 eventId를 사용한다.
이 JSON은 Pi의 로컬 음원 재생 명령이며, 음성 데이터 자체는 아니다.

| 상황 | 현재 처리 |
|---|---|
| WAITING_AUDIO 첫 음성 | 사진 후 30초가 지나도 접수 가능 |
| 완료된 마지막 성공 녹음과 동일 | SHA-256으로 확인해 기존 200 응답. 모델·DB 갱신·푸시 반복 없음 |
| 음성 완료 후 다른 녹음 | 마지막 성공 사진의 서버 처리 시작부터 30초 이내면 재분석. 세부 기준은 구현 제안 |
| 정상 사진 뒤 음성 모델 503 | WAITING_AUDIO 유지. 복구 후 같은 방문에 재시도 가능 |
| 사진 A0 뒤 음성 모델도 503 | 오류 종료를 저장하고 503 반환. 세부 값은 아래 구현 제안 |
| 음성 없이 /end 등으로 완료된 방문 | 음성 요청 409. 새 방문으로 접수 |

원본 음성은 DB나 별도 영구 파일에 저장하지 않는다.
전사문·용건·요약·배송 subtype·마지막 성공 음성 해시는 저장한다.
재전송 식별은 마지막 성공 녹음 한 건만 가능하며, 녹음 순번 계약은 TBD다.

`POST /api/v1/device/events/{eventId}/end`는 다음 JSON을 받는다.

```json
{
  "reason": "VISITOR_LEFT",
  "endedAt": "2026-10-25T00:45:00+09:00"
}
```

- reason은 VISITOR_LEFT 또는 TIMEOUT이다. DEVICE_CANCELLED는 예약 값으로 현재 400이다.
- endedAt은 필수이며 방문 발생 시각보다 빠르면 400이다.
- 세션 사진에 물품이 있으면 물품만 있음, 없으면 기타·판단 불가로 무응답 종료한다.
- 유효한 요청으로 이미 완료된 방문을 조회하면 기존 분류·종료 시각을 유지하고 200 END_SESSION을 반환한다.
- 서버 자체의 자동 세션 만료 타이머는 아직 없다.

음성 세부 동작은 [음성 구현](docs/audio-implementation.md)을 따른다.

## 분석 실패의 상태 처리

사진 A0 뒤 음성 503은 `COMPLETED`로 저장하되 HTTP 응답은 503을 유지한다.
`COMPLETED`는 접수 종료를 뜻하며 분석 성공을 보장하지 않는다.
전사문·용건·요약은 만들지 않고 `needsReview=true`를 보존한다.

`mainCategory=기타·판단 불가`는 판정표의 방향이다.
아래 세부 조합과 오류 완료 후 음성 재시도 거절은 **구현 제안이며 팀 확인 대상**이다.

| 필드 | 현재 제안 구현 값 |
|---|---|
| eventType | VISITOR_TIMEOUT: 기존 B2 코드 재사용 |
| responsePolicy | 장애 안내 |
| processingStatus | 이미지 판단 실패 |
| reason | 이미지·음성 분석 실패 |

실제 로컬 MySQL에서는 19번 방문으로 이 상태 저장과 503 반환을 확인했다.
Pi가 503을 받아 오류 음원 3번을 실제 재생하는 시험은 대기 중이다.
자세한 오류·롤백 조건은 [동시 실패 처리](docs/model-failure-handling.md)를 따른다.

## 조회·프리셋·푸시

목록의 page는 0 이상, size는 1~100이다. occurredAt 내림차순, 동률이면 eventId 내림차순이다.
목록·상세에 다음 6개 앱 표시 필드를 포함한다.

`mainCategory`, `subCategory`, `responsePolicy`, `processingStatus`, `reason`, `needsReview`

기존 eventType·purpose·status는 유지한다. 예전 기록의 분류는 null일 수 있고 needsReview의 null은 false로 응답한다.
표시 시각은 +09:00 형식이다. 사진 조회는 JPEG와 `Cache-Control: no-store`를 반환한다.

프리셋은 1 GREETING `마이크에 말씀해 주세요.`, 2 COMPLETION `접수되었습니다.`,
3 FALLBACK `일시적인 오류로 접수할 수 없습니다. 잠시 후 다시 시도해 주세요.`다.
실제 음원 재생은 Pi 담당 구현이다.

토큰 등록은 `POST /api/v1/push-tokens`, application/json이다.

```json
{
  "deviceToken": "FCM_DEVICE_TOKEN",
  "platform": "ANDROID"
}
```

신규·재등록 모두 201 빈 본문을 반환한다. 201 자체가 FCM 수신 성공을 뜻하지는 않는다.
FCM은 DB 커밋 후 비동기로 발송을 요청하며, Pi가 발송 완료를 기다리지 않는다.
사진 접수 알림과 음성·종료 결과는 같은 `event_{eventId}` 태그로 갱신한다.
잔류 물품 재사용·같은 성공 녹음 재전송·유효한 완료 방문의 종료 재요청에는 추가 알림을 요청하지 않는다.
FCM 실패가 방문 저장을 취소하지는 않는다.

Flutter 로컬 시험은 휴대폰과 PC를 같은 네트워크에 연결하고 앱에 `http://{PC_IP}:8080`을 입력한다.
앱 설정에 `/api/v1`을 붙이지 않는다. 휴대폰의 localhost는 PC가 아니다.
주소 저장 후 연결 화면뿐 아니라 새 주소로 토큰 등록·목록·알림 상세 이동까지 확인해야 한다.

## 저장·처리 구조와 현재 한계

| 구성 | 역할 |
|---|---|
| DeviceEventService | 모델 호출 조정, 파일 정리, 저장 서비스 호출, 커밋 후 푸시 요청 |
| DeviceSessionImageService | 사진 병합·분류와 물품 상태를 한 트랜잭션으로 저장 |
| DeviceSessionAudioService | 음성 상태 검사·결과·오류 종료·물품 상태 저장 |
| DeviceSessionEndService | 무음성 종료 판정·물품 상태 저장 |
| AudioModelClient / VisionModelClient | 모델 HTTP 호출과 응답 검사 |
| Classification 서비스 | 판정표 A/B/C를 앱 표시 값으로 변환 |
| SnapshotStorageService | JPEG 검증·파일 저장·읽기·삭제 |
| PackageReceptionService | 기기별 물품 존재와 미감지 횟수 관리 |
| VisitPushService | 비동기 FCM 발송과 유효하지 않은 토큰 정리 |

- 모델 HTTP 호출은 DB 트랜잭션 밖에서 실행한다. 방문·물품 상태는 함께 커밋하고 이후 푸시를 요청한다.
- 사진 파일은 Git에서 제외한다. 컨테이너 실행 시 SNAPSHOT_DIR에 영속 Volume을 연결해야 한다.
- 기존 DB 컬럼 호환을 위해 maxPackageCount·package_count를 남기지만, 새 도착 여부를 개수 증가로 판단하지 않는다.
- 사진·음성·종료를 한 프로세스의 synchronized로 순차 처리한다. 다른 장치도 모델 응답 동안 기다릴 수 있으며 여러 인스턴스 간 잠금은 없다.
- FCM은 작업 스레드 1개·대기 큐 100개다. 영구 큐·실패 재시도·사용자별 수신 대상 분리는 아직 없다.
- 모델 연결 대기 2초, 사진 읽기 대기 5초, 음성 읽기 대기 기본값 5초다. 음성은 `MODEL_AUDIO_READ_TIMEOUT_MS`로 조정한다. 전체 HTTP의 5초 상한은 아니다.
- [10/26 PR #9 실모델 시험](https://github.com/centreject/DataCat/pull/9#issuecomment-6414598771)에서 모델 담당자는 현재 순차 처리 구조의 읽기 대기를 5초로 유지할 수 있다고 보고했다. 합성 음성 기준 음성 API 최대 1.66초, 모델 단독 최대 2.11초였으며 실제 Pi 마이크·스피커 검증과는 구분한다.
- 잠금 범위를 줄여 모델 호출을 동시에 허용하거나 모델·장비를 변경하면 10초를 후보로 재측정한다. 8대 동시 요청에서 보고된 11.10초는 서버 대기를 포함한 API 응답 시간으로, 음성 읽기 대기만 늘려 해결되지 않는다.
- 모델 명세의 선택 X-Api-Key·X-Request-ID 전송은 현재 Spring 클라이언트에 연결하지 않았다.

## 자동 테스트와 수동 검증

Java 21을 사용한다. PowerShell에서 실행한다.

```powershell
cd C:\springproject\DataCat\server
.\gradlew.bat test
```

테스트는 H2 메모리 DB와 test 프로필을 사용하며 외부 MySQL·모델·FCM 없이 실행할 수 있다.
Java 21 검증 환경에서 전체 145개가 통과했다. Windows에서도 최종 `gradlew.bat test`의 BUILD SUCCESSFUL을 확인했다.
9주차 수정본은 10/28 Java 21 환경에서 전체 147개 통과(실패·오류·건너뜀 0)를 확인했다. 실행 환경 보정과 미검증 범위는 [9주차 검증 기록](docs/week9-verification.md)을 참고한다.
H2 성공만으로 실제 MySQL·Pi·모델 연동 성공을 판단하지 않는다.

PowerShell·로컬 MySQL에서 다음을 별도로 확인했다.

- 종료 API 200과 분류 저장.
- 음성 API 200, DELIVERY·전사문·요약·6개 표시 필드 저장.
- 모델 중지 중 성공 녹음 재전송 200과 기존 결과 유지.
- 정상 사진 뒤 음성 503 → 대기 유지 → 복구 후 같은 방문 완료.
- 늦은 종료 요청의 기존 결과 보존, 무음성 종료 방문의 음성 409.
- 잔류 물품 30초 이후 재사용 → 미감지 1회 유지 → 2회 해제 → 재도착 새 방문.
- 이미지·음성 분석 동시 실패의 503과 오류 종료 저장.
- 수정 Android 앱에서 접수 중·배송 결과 알림 수신, 22번 상세의 사진·전사문·배송/택배·요약 표시.
- 20번 분석 실패 알림 수신, 21번 정상 배송 결과의 API 조회.

사례 번호·상태·검증 구분은 [8주차 검증 기록](docs/week8-verification.md)을 따른다.

## 통합 확인 대기

- 현재 코드의 실제 Pi 사진·음성·종료 송수신과 프리셋·오류 음원 재생.
- 실제 모델 처리 시간 측정, 타임아웃 조정과 최신 Docker 구성 재현.
- 2차 사진·선택 종료 사진, 촬영/녹음 재전송 ID, 재접수 경계.
- 동시 실패의 오류 안내 세부 조합을 팀과 확정.

7주차에는 Android 기본 푸시 수신·알림 상세 이동을 확인했다.
8주차에는 앱 담당의 수정 APK를 적용한 뒤 접수 중·배송 결과 알림과 22번 방문 상세를 확인했다.
22번의 eventId·phone-check 기기 ID·시험 사진·전사문·배송 분류가 이번 요청과 일치했다.
앱 타임라인의 안내·녹음 문구는 상태 표시다. 실제 Pi가 음원을 재생했다는 검증으로 기록하지 않는다.
하드웨어 담당의 이전 통합 시험과 현재 브랜치의 재시험 완료를 구분한다.

## 주차별 작업

| 실제 팀플 주차 | Spring 진행 내용 |
|---|---|
| 4주차 | 프로젝트·고정 프리셋 API |
| 5주차 | MySQL·JPA·이벤트 목록·상세 조회 |
| 6주차 | 사진 접수·저장·조회·모의 Vision·방문 병합 |
| 7주차 | 사진 판정·앱 표시 6개 필드·Android 토큰·비동기 FCM |
| 8주차 | 음성·종료 API·표 B/C·재전송 보호·물품 상태 A-1·장애 복구 및 오류 종료 검증 |
