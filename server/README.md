# DataCat Spring 서버

## 개발 환경

- Java 21
- Spring Boot 4.1.1
- Gradle Wrapper

## 실행 방법

1. DataCat 저장소를 clone한다.
2. server/build.gradle을 IntelliJ에서 프로젝트로 연다.
3. Gradle JVM을 JDK 21로 설정하고 동기화한다.
4. com.datacat.server.ServerApplication을 실행한다.

기본 포트는 8080이다.

현재 구현한 프리셋 조회 API는 MySQL과 모델 서비스 없이 실행할 수 있다.
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