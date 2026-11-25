# 푸시 알림 (FCM)

새 방문이 생기면 앱을 닫아 둔 상태에서도 휴대폰에 알림이 온다. API 명세 11장 기준.

```
현관 기기 → 서버(현재: 목업 API / 이후: Spring) → FCM → 휴대폰
앱 실행 시 → POST /api/v1/push-tokens 로 토큰 등록
```

- 현재는 개인 서버의 목업 API가 토큰을 저장하고 새 방문마다 푸시를 보낸다.
- Spring으로 바꿀 때 아래 "알림 규칙"대로만 보내면 앱은 수정할 필요가 없다.
- Firebase 프로젝트는 하나만 만들고 두 서버가 같이 쓴다.

## 1. Firebase 프로젝트 만들기

1. https://console.firebase.google.com 에서 프로젝트 추가 (이름 `datacat`, 애널리틱스는 꺼도 됨)
2. 안드로이드 앱 추가
   - 패키지 이름: `com.teamdatacat.datacat_frontdoor`
   - 앱 닉네임 `DataCat 현관`, SHA-1은 비워 둠
   - `google-services.json`을 받아서 `app/datacat_frontdoor/firebase/`에 넣기
   - Gradle 설정 단계는 건너뛰어도 됨 (빌드 스크립트에서 처리)
3. 프로젝트 설정 → 서비스 계정 → 새 비공개 키 생성. 받은 파일 이름을 `firebase-service-account.json`으로 바꿔서 서버 PC의 `datacat-stack/secrets/`에 넣기

두 파일 모두 .gitignore에 들어가 있다. 서비스 계정 키가 유출되면 누구나 우리 앱으로 푸시를 보낼 수 있으니 카톡이나 깃허브에 올리지 않는다.

## 2. 서버 실행 (개인 서버 PC)

```powershell
cd C:\DataCat
git pull
cd datacat-stack
docker compose --profile tunnel up -d --build
```

`https://api.teamdatacat.com/health`에서 `"push": true`가 나오면 정상이다. false면 `secrets\firebase-service-account.json` 파일 이름과 위치를 확인한다.

## 3. 안드로이드 앱 빌드

Docker Desktop만 있으면 된다.

```powershell
cd D:\GitHub\DataCat\datacat-stack
powershell -ExecutionPolicy Bypass -File .\build-apk.ps1
```

- 처음에는 SDK와 Gradle을 받느라 10~20분 정도 걸리고, 이후에는 몇 분이면 된다.
- 결과 파일: `app\datacat_frontdoor\dist\datacat-frontdoor.apk`
- 기본 서버 주소는 `https://api.teamdatacat.com`이다. 다른 서버로 테스트할 때는 `-Api http://192.168.0.12:8090`처럼 붙인다.
- 처음 빌드하면 `app\datacat_frontdoor\android\` 폴더가 생긴다. 커밋해 두면 이후에도 같은 설정으로 빌드된다.

## 4. 휴대폰 확인

1. APK를 휴대폰에 옮겨서 설치 (출처를 알 수 없는 앱 허용 필요할 수 있음)
2. 앱 실행 후 알림 허용
3. 설정 → 휴대폰 푸시 알림이 "켜짐 · api.teamdatacat.com 서버에 등록됐어요"인지 확인
4. 같은 화면에서 테스트 방문 보내기 → 몇 초 안에 알림이 오면 정상
5. 앱을 닫아 둬도 목업 서버가 3분마다 새 방문을 만들어서 알림이 온다.
6. 알림을 누르면 해당 방문 상세 화면이 열린다.

문제가 있을 때

| 증상 | 확인할 것 |
|---|---|
| "Firebase 설정 없이 빌드됐어요" | `firebase\google-services.json` 위치 확인 후 다시 빌드 |
| "알림 권한이 꺼져 있어요" | 휴대폰 설정 → 앱 → DataCat 현관 → 알림 켜고 앱에서 다시 시도 |
| "등록하지 못했어요" | 데모 모드가 꺼져 있는지, 서버 주소가 맞는지, /health가 열리는지 |
| 등록은 됐는데 알림이 안 옴 | `https://api.teamdatacat.com/api/v1/_mock/push`에서 enabled, lastResult 확인 |
| 다시 빌드한 APK가 설치 안 됨 | 기존 앱 삭제 후 설치 (서명 키가 바뀐 경우) |

`/api/v1/_mock/push`에서 등록된 휴대폰 수, 마지막 발송 결과, 실패 이유를 볼 수 있다. 토큰은 앞뒤 일부만 표시된다.

## 5. 알림 규칙

앱과 서버가 맞춰야 하는 부분이다. Spring도 이대로 보내면 된다.

### 토큰 등록 (11.1)

앱이 켜질 때, 토큰이 바뀔 때, 서버 주소가 바뀔 때 보낸다. 같은 토큰이 다시 오면 덮어쓰면 된다.

```http
POST /api/v1/push-tokens
{ "deviceToken": "FCM 토큰", "platform": "ANDROID" }
→ 201
```

### 메시지 형식 (FCM HTTP v1)

```json
{
  "message": {
    "token": "FCM 토큰",
    "notification": { "title": "새 방문 · 배송", "body": "택배 문 앞 보관" },
    "data": { "type": "VISIT_EVENT", "eventId": "101", "tag": "event_101" },
    "android": {
      "priority": "HIGH",
      "collapse_key": "event_101",
      "notification": { "tag": "event_101" }
    }
  }
}
```

- `data.eventId`는 문자열로 넣는다. 앱은 알림을 누르면 이 값으로 `GET /api/v1/events/{eventId}`를 호출한다.
- 태그를 `event_{eventId}`로 고정한다. 같은 방문을 다시 보내면 새 알림이 쌓이지 않고 기존 알림 내용이 바뀐다.
- FCM이 404나 UNREGISTERED를 반환하면 앱이 삭제된 것이므로 해당 토큰을 지운다.

### 제목과 본문

목업 서버는 `mock-api/push.py`의 `visit_message`에서 만든다.

| 경우 | 제목 | 본문 |
|---|---|---|
| 응대 시작 (사람 감지, 벨) | 방문객이 왔어요 | 용건을 듣고 있어요 |
| 긴급 알림, 공공·긴급, 안전 확인 필요 | 긴급 · {세부 유형} | 요약 |
| 물품만 있음 | 물품 도착 · {세부 유형} | 판정 근거 |
| 그 밖의 방문 | 새 방문 · {상위 분류} | 요약 (없으면 판정 근거) |
| needsReview가 true | | 본문 끝에 " (확인 필요)" |

### 보내는 시점

명세 11장 기준이다. 경우별 상세 기준은 저장소의 `판정표.md` 5장에 있다.

- 1단계: 사진 분석 결과를 DB에 저장한 직후에 보낸다.
- 2단계: 음성 분석 결과가 나오면 같은 eventId로 알림 내용을 갱신한다.
- DB 저장이 끝난 뒤 비동기로 보낸다. Pi 응답이 FCM 발송을 기다리면 안 된다.
- 사람과 물품이 모두 없는 오탐에는 보내지 않는다.
- 문 앞에 남아 있는 같은 물품이 다시 찍히면 보내지 않는다. 새 배송은 배달 기사가 찍힌 방문으로 알린다. (판정표 표 A-1)
- 30초 안에 병합된 요청은 분류나 내용이 바뀐 경우에만 다시 보낸다.

## 6. Spring으로 옮기기

앱은 바꿀 필요가 없고 서버에서 아래 작업만 하면 된다.

### 의존성과 키

```gradle
implementation 'com.google.firebase:firebase-admin:9.+'
```

키 파일은 목업과 같은 `secrets/firebase-service-account.json`을 쓴다. compose 파일의 Spring 서비스 부분에 주석으로 넣어 두었다.

```yaml
environment:
  FCM_CREDENTIALS_FILE: /secrets/firebase-service-account.json
volumes:
  - ./secrets:/secrets:ro
```

### 토큰 테이블

```sql
CREATE TABLE push_token (
  device_token VARCHAR(512) PRIMARY KEY,
  platform     VARCHAR(16)  NOT NULL,
  created_at   DATETIME     NOT NULL,
  updated_at   DATETIME     NOT NULL
);
```

`POST /api/v1/push-tokens`가 오면 이미 있는 토큰은 updated_at만 바꾸고, 없으면 추가한 뒤 201을 반환한다.

### 발송 예시

```java
@Configuration
class FirebaseConfig {
  @Bean
  FirebaseApp firebaseApp(@Value("${FCM_CREDENTIALS_FILE}") String path) throws IOException {
    try (var in = new FileInputStream(path)) {
      return FirebaseApp.initializeApp(FirebaseOptions.builder()
          .setCredentials(GoogleCredentials.fromStream(in)).build());
    }
  }
}

@Service
@RequiredArgsConstructor
class VisitPushService {
  private final PushTokenRepository tokens;

  @Async
  public void notifyVisit(Event e) {
    String tag = "event_" + e.getId();
    for (PushToken t : tokens.findAll()) {
      Message m = Message.builder()
          .setToken(t.getDeviceToken())
          .setNotification(Notification.builder().setTitle(title(e)).setBody(body(e)).build())
          .putData("type", "VISIT_EVENT")
          .putData("eventId", String.valueOf(e.getId()))
          .putData("tag", tag)
          .setAndroidConfig(AndroidConfig.builder()
              .setPriority(AndroidConfig.Priority.HIGH)
              .setCollapseKey(tag)
              .setNotification(AndroidNotification.builder().setTag(tag).build())
              .build())
          .build();
      try {
        FirebaseMessaging.getInstance().send(m);
      } catch (FirebaseMessagingException ex) {
        if (ex.getMessagingErrorCode() == MessagingErrorCode.UNREGISTERED) tokens.delete(t);
      }
    }
  }
}
```

title(), body()는 위 제목과 본문 표대로 만든다.

### 서버 교체 순서

1. compose의 api 서비스 build 경로를 Spring 프로젝트로 바꾸고 위 환경변수와 볼륨 주석을 푼다.
2. `docker compose --profile tunnel up -d --build`
3. 휴대폰 앱은 계속 `https://api.teamdatacat.com`을 보고 있어서, 앱을 한 번 열면 새 서버에 토큰이 등록된다. 목업의 토큰 파일은 옮기지 않아도 된다.
4. 테스트 방문 보내기는 목업 전용 기능이라 Spring에서는 "지원하지 않아요"가 뜬다.

## 7. 아직 안 되는 것

- 앱의 알림·응대 정책(분류별 알림 끄기, 방해 금지 시간)은 앱 안 알림에만 적용된다. 서버에 정책 API가 생기면 서버에서 발송 여부를 판단하도록 바꾼다. (`VisitPolicy.toJson()` 형식)
- 아이폰은 애플 개발자 계정과 Mac이 필요해서 이번에는 안드로이드만 지원한다.
- 웹(app.teamdatacat.com)은 푸시를 받지 않고 기존처럼 15초마다 새 방문을 확인한다.
- 로그인 기능이 없어서 등록된 모든 휴대폰에 같은 알림이 간다. (명세상 인증은 3단계)
