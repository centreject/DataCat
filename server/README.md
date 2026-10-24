# DataCat Spring 서버

## 개발 환경

- Java 21
- Spring Boot 4.1.1
- Gradle Wrapper

## 현재 구현 범위 — 팀플 7주차

- 사진 접수·저장·조회, Vision 호출, 30초 방문 병합
- 판정표 A0~A5와 병합 시 판정 우선순위
- 목록·상세 응답의 앱 표시 필드 6개
- Android 푸시 토큰 등록, 방문 저장 커밋 후 비동기 FCM 발송
- 서비스·API 자동 테스트와 실제 Android 알림 수신·상세 화면 이동 확인

문 앞 물품 상태용 코드와 테스트는 작성했으나 사진 접수 흐름 연결은 남아 있다.
Pi 담당이 이전 feature/image-upload의 실제 장치·모델·Docker 시험을 별도로 진행했다.
현재 푸시 브랜치를 반영한 재시험과 실행 구성 재현, 2차 사진·음성·종료 API는 후속 작업이다.
이 문서의 5·6주차 검증 결과는 당시 기록이며, 현재 변경 동작은 7주차 절을 따른다.

## 실행 방법

1. DataCat 저장소를 clone한다.
2. server/build.gradle을 IntelliJ에서 프로젝트로 연다.
3. Gradle JVM을 JDK 21로 설정하고 동기화한다.
4. 로컬 MySQL을 실행하고 datacat 데이터베이스를 생성한다.
5. ServerApplication 실행 설정의 환경변수에 DB_USERNAME과 DB_PASSWORD를 지정한다.
6. 샘플 데이터가 필요하면 Active profiles에 dev를 입력한다.
7. com.datacat.server.ServerApplication을 실행한다.

기본 포트는 8080이다.

현재 서버 실행에는 MySQL 연결이 필요하다.
프리셋·이벤트 조회에는 모델 서비스가 필요하지 않다.
정상 이미지 판정을 시험하려면 모델 서비스가 실행 중이어야 한다.
현재 모델 호출 실패는 A0로 기록하고 음성 대기 응답을 반환한다. 자세한 규칙은 7주차 절을 따른다.
Spring 서버는 모델 서비스가 꺼져 있어도 시작할 수 있다.
Docker 실행 환경은 추후 추가한다.

## 구현된 API

### GET /api/v1/presets

고정된 프리셋 목록을 반환한다.

요청 본문은 없다.

응답 예시:

```json
[
  {
    "presetId": 1,
    "type": "GREETING",
    "text": "마이크에 말씀해 주세요."
  },
  {
    "presetId": 2,
    "type": "COMPLETION",
    "text": "접수되었습니다."
  },
  {
    "presetId": 3,
    "type": "FALLBACK",
    "text": "일시적인 오류로 접수할 수 없습니다. 잠시 후 다시 시도해 주세요."
  }
]
```
예상 결과: HTTP 200과 프리셋 3개를 포함한 JSON 배열.
인사·접수 완료·오류 안내 3종을 제공한다.
오류 안내의 ID 3과 FALLBACK 타입은 기존 앱 목업과 맞췄다.
실제 음성 재생은 Pi에 저장된 고정 음원을 사용한다.

Windows PowerShell 확인 명령:

```powershell
curl.exe -i http://localhost:8080/api/v1/presets
```

예상 결과: HTTP 200과 프리셋 3개를 포함한 JSON 배열.

## 이벤트 조회 API — 5주차

### 구현 내용

- MySQL 연결 및 JPA 설정
- Event Entity와 EventRepository
- 이벤트 목록·상세 조회 API
- 최근 발생 시각 순 정렬 및 페이지 조회
- 한국 시간(+09:00) 기준 응답
- 오류 응답을 `code`, `message` 형식으로 처리
- dev 프로필에서만 실행되는 샘플 데이터 생성

### 로컬 실행 설정

먼저 로컬 MySQL에 `datacat` 데이터베이스를 생성합니다.

DBeaver에서 로컬 MySQL 연결의 SQL 편집기를 열고 실행합니다.

```sql
CREATE DATABASE IF NOT EXISTS datacat
    CHARACTER SET utf8mb4;
```

IntelliJ의 ServerApplication 실행 설정에 다음 환경변수를 지정합니다.

| 환경변수 | 값 |
|---|---|
| DB_USERNAME | 본인의 MySQL 사용자 이름 |
| DB_PASSWORD | 본인의 MySQL 비밀번호 |
| DB_URL | 선택 사항. 기본값: jdbc:mysql://localhost:3306/datacat |

비밀번호는 application.properties에 직접 입력하지 않습니다.
IntelliJ에서 지정한 환경변수는 해당 실행 설정에 적용됩니다.

현재 `spring.jpa.hibernate.ddl-auto=update`는 개발용 설정입니다.

### 개발용 샘플 데이터

IntelliJ 실행 설정의 Active profiles에 `dev`를 입력합니다.

- events 테이블이 비어 있으면 샘플 3건을 저장합니다.
- 데이터가 하나라도 있으면 샘플 생성을 건너뜁니다.
- dev 프로필을 사용하지 않으면 샘플 생성 코드는 실행되지 않습니다.
- 이미 DB에 저장된 데이터는 프로필 변경이나 서버 재시작으로 삭제되지 않습니다.
- 샘플은 실제 장치에서 발생한 방문 이벤트가 아닙니다.

### 조회 API

| Method | URL | 설명 |
|---|---|---|
| GET | /api/v1/events?page=0&size=20 | 이벤트 목록 조회 |
| GET | /api/v1/events/{eventId} | 이벤트 상세 조회 |

페이지 번호는 0부터 시작합니다.
page의 기본값은 0, size의 기본값은 20입니다.

이번 구현의 제안 제한:
- page: 0 이상
- size: 1~100
- eventId: 1 이상

정렬은 occurredAt 내림차순이며, 발생 시각이 같으면 eventId 내림차순입니다.

### 오류 응답

```json
{
  "code": "NOT_FOUND",
  "message": "해당 이벤트를 찾을 수 없습니다."
}
```

이벤트 조회 API의 구현 오류 코드:

| HTTP 상태 | code | 상황 |
|---|---|---|
| 400 | INVALID_REQUEST | 잘못된 값 또는 숫자 형식 오류 |
| 404 | NOT_FOUND | 해당 이벤트 없음 |
| 500 | INTERNAL_SERVER_ERROR | 예상하지 못한 서버 처리 오류 |

### 수동 검증 결과

PowerShell의 curl.exe로 다음 결과를 확인했습니다.

- 빈 목록 조회: 200, 빈 content
- 존재하지 않는 이벤트 조회: 404
- 음수 page: 400
- 문자 page: 400
- 샘플 목록 조회: 200, 총 3건, 최신순
- 샘플 상세 조회: 200
- size=2 페이지 조회: 첫 페이지 2건, 두 번째 페이지 1건
- 발생 시각: +09:00 형식
- 서버 재시작 후 샘플 총 3건 유지: 중복 생성 없음

### 5주차 구현 범위

5주차 구현에서는 eventType을 비워 두었습니다. 현재 사진 판정 값은 7주차 절을 따릅니다.
샘플의 음성 분석 결과와 사진 정보는 null입니다.

5주차에서는 이벤트 조회 기능을 구현했습니다.
사진 업로드·조회와 Vision 호출은 아래 6주차 항목에서 추가했습니다.

## 사진 접수·조회 및 Vision 연동 — 6주차

### 구현 내용

- Pi의 이벤트 메타데이터와 JPEG 사진 접수
- 사진 파일 저장 및 Event 연결
- Vision 모델 서비스 호출과 응답 형식 검사
- 거리값과 Vision 결과 JSON 저장
- 사람 감지 여부에 따른 Pi 동작 응답
- 같은 장치의 30초 이내 요청 병합
- 사진 교체 후 이전 파일 정리
- 모델 호출·DB 저장 실패 시 새 사진 정리
- 이벤트 사진 조회 API
- 업로드·JSON·모델 장애 오류 응답 처리

### 실행 환경

이번 검증은 다음 환경에서 진행했습니다.

- Spring: Windows IntelliJ
- MySQL: 로컬 MySQL
- 모델: Docker의 모의 모델 서비스
- Pi 요청: PowerShell curl.exe로 대체
- 사진 조회: 웹 브라우저

6주차 당시 실제 Pi·Flutter·실제 인식 모델을 연결한 검증은 진행하지 않았습니다.
7주차에는 실제 Android Flutter 앱의 알림 수신·상세 이동을 추가 확인했습니다.

### 추가 환경변수

| 환경변수 | 기본값 | 역할 |
|---|---|---|
| MODEL_SERVICE_URL | http://localhost:8000 | 모델 서비스 루트 주소 |
| SNAPSHOT_DIR | ./data/snapshots | 사진 저장 폴더 |

MODEL_SERVICE_URL에는 /internal/v1을 붙이지 않습니다.
상대 저장 경로는 Spring 프로세스의 실행 폴더를 기준으로 합니다.

사진 파일은 Git에서 제외하며, DB에는 저장 폴더 기준 파일 이름을 기록합니다.
Docker 배포 시 사진 저장 폴더에 Volume을 연결해야 합니다.
Spring·MySQL·모델의 전체 Docker Compose 통합은 이후 작업입니다.

### 사진 접수 API

POST /api/v1/device/events

Content-Type: multipart/form-data

| 파트 | 파트 Content-Type | 내용 |
|---|---|---|
| metadata | application/json | 이벤트 메타데이터 |
| image | image/jpeg | JPEG 사진 |

metadata 예시:

```json
{
  "deviceId": "door-01",
  "triggerType": "TOF",
  "distanceMm": 1850,
  "capturedAt": "2026-10-12T16:00:00+09:00"
}
```

- deviceId: 비어 있지 않은 100자 이하 문자열
- triggerType: TOF 또는 BUTTON
- capturedAt: 시간대 정보가 있는 촬영 시각
- distanceMm: 생략 가능, 제공하면 0 이상
- distanceMm은 기록용이며 방문객 이탈 판단에 사용하지 않습니다.

### 업로드 제한

- 파일 한 개: 최대 16MB
- 전체 multipart 요청: 최대 17MB
- 이미지 해상도: 최대 40MP
- 실제로 읽을 수 있는 JPEG만 허용

전체 요청 17MB는 메타데이터와 multipart 부가 정보를 고려한 구현 제안값입니다.

### Pi 응답

신규 이벤트는 201, 기존 이벤트 병합은 200을 반환합니다.

사람 감지:

```json
{
  "eventId": 4,
  "status": "WAITING_AUDIO",
  "action": "START_RECEPTION",
  "preset": {
    "presetId": 1,
    "text": "마이크에 말씀해 주세요."
  }
}
```

사람 미감지:

```json
{
  "eventId": 6,
  "status": "COMPLETED",
  "action": "SILENT_STANDBY"
}
```

위 예시는 6주차의 기본 분기입니다. 현재는 버튼·물품·LOW_VISIBILITY·모델 장애까지
판정표 A0~A5를 적용합니다. 세부 규칙은 아래 7주차 절과 API_v1_5.md 6.1을 따릅니다.

### 이벤트 병합

- 같은 deviceId의 마지막 성공 사진 수신 시각이 30초 이내면 기존 이벤트를 재사용합니다.
- 기준 시각은 서버가 해당 요청 처리를 시작한 시각입니다.
- 성공 요청마다 수신 시각을 갱신하므로 마지막 성공 요청 기준으로 판단합니다.
- 최초 eventId, occurredAt, triggerType은 유지합니다.
- 사진·거리값·Vision 결과는 갱신합니다. 현재 분류·상태·종료 시각은 7주차의 우선순위 규칙에 따라 변경하거나 유지합니다.
- DB 저장 성공 후 이전 사진을 삭제합니다.

30초는 명세의 시작값이며 실측 후 조정할 수 있습니다.
현재 synchronized로 한 Spring 프로세스의 이벤트 생성 요청을 순차 처리합니다.
모든 장치 요청이 대기할 수 있으며, 여러 서버 인스턴스 간 동시성을 제어하지는 않습니다.

### 사진 조회

GET /api/v1/events/{eventId}/snapshot

- 성공: 200, Content-Type: image/jpeg
- 이벤트 또는 사진 없음: 404
- 성공 응답은 JSON이 아닌 JPEG 파일 데이터입니다.
- Cache-Control: no-store를 사용합니다.

### 모델 호출

POST /internal/v1/vision/detect

multipart image 파트에 JPEG와 파일 이름을 전달합니다.
detections의 구조와 confidence의 0~1 범위를 검사합니다.
추가 JSON 필드는 무시하며, 모르는 라벨은 사람 감지에 사용하지 않습니다.

연결 대기 2초, 응답 읽기 대기 5초를 시작 설정으로 사용합니다.
전체 요청 시간의 5초 상한을 의미하지는 않습니다.
6주차에는 모델 호출 실패 시 503을 반환했습니다.
현재 VisionModelClient의 503 예외는 사진 접수 서비스에서 A0 판정으로 처리합니다.

### 오류 응답

JSON 오류 응답은 code와 message 형식을 사용합니다.

| HTTP 상태 | 코드 |
|---|---|
| 400 | INVALID_REQUEST |
| 404 | NOT_FOUND |
| 405 | METHOD_NOT_ALLOWED |
| 409 | EVENT_STATE_CONFLICT |
| 415 | UNSUPPORTED_MEDIA_TYPE |
| 500 | INTERNAL_SERVER_ERROR |
| 503 | MODEL_SERVICE_UNAVAILABLE (ModelClient의 예외 코드. 현재 사진 접수에서는 A0로 처리) |

415 및 추가 서버 오류 코드는 이번 구현의 제안값입니다.
현재 모델 호출 실패는 A0로 처리하므로 사진·Event를 저장할 수 있습니다.
파일·DB 등 다른 오류로 요청 처리가 실패하면 새 사진을 정리합니다.
별도의 FAILED 이벤트 기록은 현재 구현하지 않았습니다.

### 6주차 수동 검증 결과

- [x] 모의 모델 /health: 200, profile=mock
- [x] 사람 감지 업로드: 201, WAITING_AUDIO, START_RECEPTION
- [x] 이벤트 상세·목록 조회: 200, 사진 URL 포함
- [x] 브라우저에서 저장된 JPEG 표시
- [x] 연속 재요청: 201 이후 200, 같은 eventId 유지
- [x] 병합 요청 두 번에도 이벤트 한 건만 증가
- [x] 물품만 감지: COMPLETED, SILENT_STANDBY, preset 생략
- [x] 완료 이벤트의 endedAt 저장
- [x] 사진 누락: 400
- [x] 가짜 JPEG: 400
- [x] 모델 중지: 503
- [x] 모델 재시작: /health 200
- [x] 실패 테스트 전후 이벤트 6건·사진 3개 유지

위 모델 중지 503·실패 전후 건수는 6주차 당시 결과입니다. 현재 A0 처리의 결과를 뜻하지 않습니다.

모의 모델은 파일 이름으로 감지 결과를 선택합니다.
이번 결과는 통신·저장·분기 검증이며 실제 이미지 인식 정확도 검증은 아닙니다.
최초 구현 시 빌드와 수동 연동 테스트를 확인했습니다.
PR 리뷰 반영 과정에서 H2 기반 test 프로필을 추가했으며,
gradlew.bat test로 contextLoads 테스트가 통과했습니다.

## 이미지 판정·앱 표시·비동기 푸시 — 팀플 7주차

### 이미지 판정

판정 기획 담당의 판정표 A를 ImageClassificationService에 구현했습니다.
위에서 처음 일치하는 규칙을 사용합니다. distanceMm은 판정이 아닌 기록용입니다.

| 규칙 | 조건 | 결과 |
|---|---|---|
| A0 | 모델 연결·응답 실패 | WAITING_AUDIO, 일반 접수, 이미지 판단 실패, needsReview=true |
| A1 | 사람 감지 | WAITING_AUDIO, 일반 접수 |
| A2 | 사람이 없어도 BUTTON으로 시작 | WAITING_AUDIO, 일반 접수 |
| A3 | TOF, 사람 없음, 물품 있음 | COMPLETED, UNATTENDED_DELIVERY, 물품만 있음 |
| A4 | TOF, 사람·물품 없음, LOW_VISIBILITY | COMPLETED, CAMERA_BLOCKED, 안전 확인 필요 |
| A5 | 그 외 또는 동물만 감지 | COMPLETED, NO_VISITOR, 알림 없음 |

A0~A2는 START_RECEPTION과 프리셋 1을 반환하고, A3~A5는 SILENT_STANDBY를 반환합니다.
A1/A2에서 LOW_VISIBILITY이면 needsReview=true이며, A1에서 2명 이상이면 복수 방문자로 표시합니다.
모델 장애가 A0로 처리되고 저장에 성공하면 신규 요청은 201, 병합은 200입니다.
이는 현재 Spring에서 음성 처리가 완료된다는 뜻이 아닙니다. 음성 API는 이후 구현합니다.

### 30초 병합 시 기존 판정 유지

- 사진·거리값·Vision 결과·수신 시각을 갱신하고 물품 최대 감지 수를 기록합니다.
- 기존 판정이 없으면 새 판정을 적용합니다.
- 기존 판정이 있으면 새 A0로 덮어쓰지 않습니다.
- 나머지는 A0~A5에서 새 판정의 순서가 더 앞설 때만 분류·상태·종료 시각을 바꿉니다.
- 같은 규칙 또는 더 낮은 우선순위면 기존 분류를 유지하고 추가 푸시를 보내지 않습니다.
- 예: A3 다음 A1은 변경·알림 갱신, A1 다음 A3는 기존 음성 대기 유지입니다.

### 앱 표시 필드 6개

이벤트 목록의 각 항목과 상세 응답에 다음 값을 추가했습니다.

| JSON 필드 | 앱 표시 |
|---|---|
| mainCategory | 분류 |
| subCategory | 세부 분류 |
| responsePolicy | 응대 방식 |
| processingStatus | 처리 상태 |
| reason | 판정 이유 |
| needsReview | 확인 필요 여부 |

status는 진행 단계이고 processingStatus는 판정 과정의 상태이므로 별개입니다.
기존 데이터의 문자열 필드는 null일 수 있으며, needsReview가 DB에서 null이면 API는 false를 반환합니다.
A0~A2의 mainCategory·subCategory·eventType은 음성으로 용건을 확정하기 전까지 null입니다.
현재 사진 단계에서는 purpose·transcript·summary도 비어 있습니다.

### 푸시 토큰 등록

POST /api/v1/push-tokens

Content-Type: application/json

```json
{
  "deviceToken": "FCM_DEVICE_TOKEN",
  "platform": "ANDROID"
}
```

- 앱이 Firebase에서 받은 FCM 등록 토큰을 서버에 전달합니다.
- 신규와 동일 토큰 재등록 모두 201이며 응답 본문은 없습니다.
- 같은 토큰은 중복 저장하지 않고 등록 시각을 갱신합니다. 대소문자는 구별합니다.
- 토큰은 공백만인 값 불가·최대 512자이며 platform은 ANDROID만 허용합니다.
- 토큰 형식을 통과해 저장했다는 뜻이므로 201만으로 FCM 수신 성공을 판단하지 않습니다.

### FCM 실행 설정

| 환경변수 | 기본값 | 역할 |
|---|---|---|
| FCM_ENABLED | false | true일 때 실제 FCM 발송 사용 |
| FCM_CREDENTIALS_FILE | 빈 값 | 앱과 같은 Firebase 프로젝트의 서버용 서비스 계정 JSON 경로 |

기존 DB 환경변수와 함께 IntelliJ의 ServerApplication 실행 설정에 지정합니다.
서비스 계정 JSON은 저장소 밖에 보관하며 Git에 올리지 않습니다.
FCM_ENABLED=true이면 읽을 수 있는 키 파일이 필요합니다. false이면 Firebase 설정 없이 발송만 생략합니다.
토큰 등록과 나머지 서버 API는 FCM을 끈 상태에서도 사용할 수 있습니다.

예시 경로: `C:\springproject\datacat-secrets\firebase-service-account.json`

### 비동기 발송 흐름

1. DeviceEventService가 사진 분석·분류를 수행합니다.
2. EventRepository.saveAndFlush가 자체 트랜잭션으로 방문 저장을 마치고 커밋합니다.
3. 신규 또는 분류가 변경된 A0~A4이면 VisitPushService에 알림을 요청합니다.
4. 메시지 값을 복사해 별도 작업 큐에 넣고 Pi 응답을 생성합니다.
5. 별도 스레드가 등록된 Android 토큰을 조회해 FCM으로 발송합니다.

현재 DeviceEventService에 외부 트랜잭션이 없다는 전제의 순서입니다.
이후 서비스 전체에 @Transactional을 추가하면 커밋 이후 발송 시점을 다시 맞춰야 합니다.

Pi 응답은 Vision·DB 처리를 기다리지만 FCM의 네트워크 응답은 기다리지 않습니다.
사진 접수 자체는 기존 synchronized 방식으로 한 요청씩 처리하므로 여러 장치의 분석 병렬 처리를 구현한 것은 아닙니다.

- WAITING_AUDIO 알림: 제목 방문객이 왔어요 / 본문 용건을 듣고 있어요
- 같은 eventId의 data.tag·Android notification.tag·collapse key: event_{eventId}
- data.eventId는 문자열이며 앱이 알림을 누르면 상세 API를 호출합니다.
- needsReview=true이면 본문에 (확인 필요)를 덧붙입니다.
- 작업 스레드 1개, 대기 큐 100개입니다. 초과·발송 실패는 로그를 남기고 Pi 응답에 전파하지 않습니다.
- 등록된 Android 토큰 전체로 보냅니다. 사용자별 수신 분리·발송 재시도·영구 큐는 없습니다.
- UNREGISTERED 토큰만 삭제합니다. 다른 오류는 기록하고 다음 토큰을 처리합니다.

### 물품 상태 코드의 현재 범위

DevicePackageState·PackageReceptionService와 서비스 테스트를 작성했습니다.
같은 물품 재감지 시 기존 이벤트 재사용, 물품 증가 시 신규 생성, 감소해도 최대 개수 유지, 상태 삭제 후 방문 기록 유지 동작을 서비스 단위로 검증했습니다.

현재 DeviceEventService는 PackageReceptionService를 호출하지 않습니다.
따라서 HTTP 사진 접수에서 30초 이후 같은 물품의 이벤트·알림 반복을 막는 기능은 아직 완료하지 않았습니다.
일반 방문 병합과 물품 추가 이벤트의 적용 순서, 사용하지 않은 새 사진 정리, A5 시 상태 초기화·음성/종료 시 상태 기록을 연결해야 합니다.

### 실제 Android 앱 푸시 시험 — 2026-10-21

| 항목 | 시험 환경 |
|---|---|
| Spring / MySQL | Windows IntelliJ / 로컬 MySQL |
| Vision | Docker 모의 모델 서비스 |
| Pi 입력 | PowerShell의 JPEG·metadata 업로드로 대체 |
| 앱 / 알림 | 실제 Android Flutter APK / Firebase FCM |

- [x] 앱의 접속 대상을 로컬 Spring 주소로 설정하고 연결 확인
- [x] 앱의 푸시 등록 상태가 로컬 Spring 주소를 가리키는지 확인
- [x] 새 deviceId의 사람 감지 요청으로 방문 접수
- [x] Spring의 해당 eventId FCM 발송 성공 로그 확인
- [x] 앱을 백그라운드로 둔 휴대폰에 실제 알림 표시
- [x] 알림을 눌러 해당 방문 상세와 사진 확인
- [x] 새 방문 요청으로 재시험하여 방문객이 왔어요 / 용건을 듣고 있어요 표시 확인

이 시험은 Spring·FCM·Android 앱 연결을 확인한 결과입니다.
모의 Vision은 파일 이름으로 결과를 선택하므로 실제 사람 인식 정확도 시험이 아닙니다.
용건을 듣고 있어요는 WAITING_AUDIO 안내이며 실제 음성 녹음·STT·용건 분석 완료를 뜻하지 않습니다.
Pi 담당은 2026-10-18 이전 feature/image-upload와 실제 모델을 사용해 Pi 사진 전송·응대 지시·녹음까지 별도로 확인했습니다.
해당 시험은 음성·종료 API가 없어 404로 중단됐으며, 현재 푸시 브랜치를 반영한 재시험은 8주차 작업으로 진행합니다.

앱 설정의 테스트 방문 보내기는 목업 서버 전용입니다.
Spring 검증은 POST /api/v1/device/events로 요청하며 목업 전용 API 성공을 기준으로 삼지 않습니다.

## 남은 작업

- 판정표 A-1과 사진 접수의 연결·반복 물품 알림 억제 통합 검증
- 현재 푸시 브랜치 반영 후 실제 Pi·Vision 재시험 및 타임아웃 조정
- Pi 담당의 Docker 실행 구성을 확인하고 현재 브랜치로 재현
- 2차 사진·음성·종료 API와 후속 프리셋 응대
- 이후 음성·종료 결과의 동일 방문 알림 갱신

## 자동 테스트

테스트 실행에는 Java 21이 필요합니다.

```powershell
cd server
.\gradlew.bat test
```

ServerApplicationTests는 test 프로필을 사용합니다.
src/test/resources/application-test.properties에서 H2 메모리 DB를 설정합니다.
FCM은 test 프로필에서 끕니다. 현재 자동 테스트는 외부 MySQL·실행 중인 모델·실제 Firebase 키 없이 실행합니다.

실제 서버 실행은 기존 MySQL 설정을 사용합니다.

| 테스트 클래스 | 검증 범위 |
|---|---|
| ServerApplicationTests | H2 test 프로필에서 애플리케이션 시작 |
| EventImageStateTests | 추가 사진 수신 시 상태 보존·물품 최대 수 유지 |
| DeviceEventServiceTests | 방문 저장 후 푸시 요청, 병합 우선순위, 모델 실패 A0, DB 실패 정리, A5 알림 생략 |
| PackageReceptionServiceTests | 물품 상태 서비스의 재감지·추가 감지·상태 초기화. HTTP 흐름 연결 시험은 아님 |
| PushTokenRegistrationTests | 신규·재등록, 대소문자 구별, 잘못된 토큰·플랫폼 요청 |
| VisitPushServiceTests | 큐 등록·메시지 값 보존·태그·FCM 꺼짐·큐 거부·UNREGISTERED 정리·다른 토큰 계속 처리 |

2026-10-21 Windows Java 21에서 다음 명령의 BUILD SUCCESSFUL을 확인했습니다.

```powershell
.\gradlew.bat test --rerun-tasks
```

H2·모의 객체 테스트는 실제 MySQL·Pi·인식 모델·FCM 통합 시험을 대체하지 않습니다.
Firebase SDK deprecated API 안내는 현재 경고이며 테스트 실패는 아닙니다.
