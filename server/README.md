# DataCat Spring 서버

## 개발 환경

- Java 21
- Spring Boot 4.1.1
- Gradle Wrapper

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
사진 업로드 API를 사용하려면 모델 서비스가 실행 중이어야 한다.
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
  }
]
```

Windows PowerShell 확인 명령:

```powershell
curl.exe -i http://localhost:8080/api/v1/presets
```

예상 결과: HTTP 200과 프리셋 2개를 포함한 JSON 배열.

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

### 현재 구현 범위

eventType은 최종 분류 정책 확정 전까지 null을 허용합니다.
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

실제 Pi·Flutter·실제 인식 모델을 연결한 검증은 아직 진행하지 않았습니다.

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

현재 person 라벨 존재 여부를 사용하는 잠정 분기입니다.
신뢰도 임계값·LOW_VISIBILITY 처리·최종 eventType·세부 응대 정책은
분류 기획에 맞춰 추가 검토합니다.

### 이벤트 병합

- 같은 deviceId의 마지막 성공 사진 수신 시각이 30초 이내면 기존 이벤트를 재사용합니다.
- 기준 시각은 서버가 해당 요청 처리를 시작한 시각입니다.
- 성공 요청마다 수신 시각을 갱신하므로 마지막 성공 요청 기준으로 판단합니다.
- 최초 eventId, occurredAt, triggerType은 유지합니다.
- 사진·거리값·Vision 결과·상태·종료 시각은 새 결과로 갱신합니다.
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
모델 호출 실패 시 503 MODEL_SERVICE_UNAVAILABLE을 반환합니다.

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
| 503 | MODEL_SERVICE_UNAVAILABLE |

415 및 추가 서버 오류 코드는 이번 구현의 제안값입니다.
모델 호출 실패 시 Event를 새로 저장하지 않고 새 사진을 정리합니다.
별도의 FAILED 이벤트 기록은 현재 구현하지 않았습니다.

### 수동 검증 결과

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

모의 모델은 파일 이름으로 감지 결과를 선택합니다.
이번 결과는 통신·저장·분기 검증이며 실제 이미지 인식 정확도 검증은 아닙니다.
최초 구현 시 빌드와 수동 연동 테스트를 확인했습니다.
PR 리뷰 반영 과정에서 H2 기반 test 프로필을 추가했으며,
gradlew.bat test로 contextLoads 테스트가 통과했습니다.

### 후속 작업

- 실제 Pi·Flutter·Vision 모델 통합
- 이벤트 분류 정책 보완
- 앱 알림
- 전체 Docker 실행 구성
- 음성 접수와 후속 프리셋 응대

## 자동 테스트

테스트 실행에는 Java 21이 필요합니다.

```powershell
cd server
.\gradlew.bat test
```

ServerApplicationTests는 test 프로필을 사용합니다.
src/test/resources/application-test.properties에서 H2 메모리 DB를 설정하므로,
기본 contextLoads 테스트에 외부 MySQL이나 실행 중인 모델 서비스가 필요하지 않습니다.

실제 서버 실행은 기존 MySQL 설정을 사용합니다.
H2 테스트는 애플리케이션 시작을 검증하며, 실제 MySQL·모델 연동 검증을 대체하지 않습니다.

검증 결과: gradlew.bat test 성공.