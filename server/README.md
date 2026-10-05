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
모델 서비스는 현재 구현된 프리셋·이벤트 조회 API 실행에 필요하지 않다.
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

## 이벤트 조회 API — 2주차

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

사진 업로드·조회, 모델 연동, 장치 명령, 앱 알림은 이후 단계에서 구현합니다.