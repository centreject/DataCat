# 휴대폰 푸시 알림 (FCM)

새 방문이 생기면 앱을 닫아 둬도 휴대폰 알림창에 뜹니다. API 명세 11장을 따릅니다.

```
현관 기기 → 서버(지금: 목업 API / 나중: Spring) ──FCM──▶ 휴대폰 알림
                     ▲                                       │
                     └──── POST /api/v1/push-tokens ◀──── 앱이 켜질 때 토큰 등록
```

- **지금:** 내 개인 서버(목업 API)가 토큰을 저장하고 새 방문마다 푸시를 보냅니다.
- **나중:** Spring 서버가 같은 규칙으로 보내면, 앱은 고칠 것 없이 그대로 받습니다. 아래 [Spring 으로 옮기기](#spring-으로-옮기기) 참고.
- Firebase 프로젝트는 하나만 만들어서 두 서버가 같이 씁니다.

---

## 1단계. Firebase 프로젝트 만들기 (10분, 한 번만)

1. https://console.firebase.google.com → **프로젝트 추가** → 이름 `datacat` (Google 애널리틱스는 꺼도 됨)
2. 프로젝트 화면에서 **안드로이드 아이콘**(앱 추가)
   - Android 패키지 이름: **`com.teamdatacat.datacat_frontdoor`** (정확히 이대로)
   - 앱 닉네임: `DataCat 현관` / SHA-1 은 비워 둠
   - **`google-services.json` 다운로드** → `app/datacat_frontdoor/firebase/` 폴더에 넣기
   - 나머지 단계(Gradle 설정 등)는 **건너뛰기** — 빌드 스크립트가 알아서 함
3. ⚙ **프로젝트 설정 → 서비스 계정 → 새 비공개 키 생성** → 받은 파일 이름을
   **`firebase-service-account.json`** 으로 바꿔서 서버 PC 의 `datacat-stack/secrets/` 에 넣기

> 두 파일 모두 git 에 올라가지 않게 막아 두었습니다. 특히 **서비스 계정 키는 카톡·깃허브에 올리면 안 됩니다** (누구나 우리 앱에 푸시를 보낼 수 있게 됨).

## 2단계. 서버(개인 서버 PC)에서 켜기

```powershell
cd C:\DataCat
git pull
cd datacat-stack
docker compose --profile tunnel up -d --build
```

확인: 브라우저에서 `https://api.teamdatacat.com/health` → `"push": true` 가 보이면 성공.
`false` 면 `secrets\firebase-service-account.json` 파일 이름·위치를 확인하세요.

## 3단계. 안드로이드 앱 만들기 (내 PC, Docker Desktop 만 있으면 됨)

```powershell
cd D:\GitHub\DataCat\datacat-stack
powershell -ExecutionPolicy Bypass -File .\build-apk.ps1
```

- 처음엔 10~20분 걸립니다 (안드로이드 SDK·Gradle 다운로드). 다음부터는 몇 분.
- 결과: `app\datacat_frontdoor\dist\datacat-frontdoor.apk`
- 앱이 처음 연결할 서버는 `https://api.teamdatacat.com` 입니다. 다른 서버로 시험하려면 `-Api http://192.168.0.12:8090` 을 붙입니다.
- 처음 빌드하면 `app\datacat_frontdoor\android\` 폴더가 생깁니다. 커밋해 두면 다음부터 같은 설정으로 빌드됩니다.

## 4단계. 휴대폰에 설치하고 확인

1. APK 를 휴대폰으로 옮겨(카톡 나에게 보내기, USB 등) 설치. "출처를 알 수 없는 앱" 허용이 필요할 수 있어요.
2. 앱 실행 → **알림 허용**
3. 앱 **설정 → 휴대폰 푸시 알림** 이 `켜짐 · api.teamdatacat.com 서버에 등록됐어요` 인지 확인
4. 같은 화면의 **테스트 방문 보내기 → 보내기** → 몇 초 뒤 알림이 오면 성공
5. 앱을 완전히 닫고 기다려도 됩니다. 목업 서버가 3분마다 새 방문을 만들고 푸시를 보냅니다.
6. 알림을 누르면 그 방문의 상세 화면이 열립니다.

### 안 될 때

| 증상 | 확인 |
|---|---|
| 설정에 "Firebase 설정 없이 빌드됐어요" | `firebase\google-services.json` 위치 확인 후 다시 빌드 |
| "알림 권한이 꺼져 있어요" | 휴대폰 설정 → 앱 → DataCat 현관 → 알림 켜기 → 앱 설정에서 다시 시도 |
| "등록하지 못했어요" | 데모 모드가 꺼져 있는지, 서버 주소가 맞는지, `https://api.teamdatacat.com/health` 가 열리는지 |
| 등록은 됐는데 알림이 안 옴 | `https://api.teamdatacat.com/api/v1/_mock/push` 를 열어 `enabled`, `lastResult` 확인 |
| 다시 빌드한 APK 가 "앱이 설치되지 않음" | 이전 앱을 지우고 설치 (서명 키가 바뀐 경우) |

`/api/v1/_mock/push` 는 등록된 휴대폰 수, 마지막 발송 결과, 실패 이유를 보여 줍니다. 토큰은 앞뒤만 보입니다.

---

## 알림 규칙 (서버가 지킬 것)

앱과 서버 사이 약속은 이것뿐입니다. Spring 도 이대로 보내면 됩니다.

**토큰 등록 (API 11.1)** — 앱이 켜질 때, 토큰이 바뀔 때, 서버 주소가 바뀔 때마다 보냅니다. 같은 토큰이 여러 번 와도 덮어쓰면 됩니다.

```http
POST /api/v1/push-tokens
{ "deviceToken": "FCM 토큰", "platform": "ANDROID" }
→ 201
```

**보내는 메시지 (FCM HTTP v1)**

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

- `data.eventId` 는 **문자열**. 앱은 알림을 누르면 `GET /api/v1/events/{eventId}` 로 상세를 불러옵니다.
- `tag` 를 `event_{eventId}` 로 고정 → 세션 병합으로 같은 방문을 다시 보내면 알림이 새로 쌓이지 않고 **덮어써집니다** (API 11.1 인플레이스 갱신).
- 제목·본문 (목업 서버 기준, `mock-api/push.py` 의 `visit_message`)

  | 경우 | 제목 | 본문 |
  |---|---|---|
  | 긴급 알림 / 공공·긴급 / 안전 확인 필요 | `긴급 · {세부 유형}` | 요약 |
  | 물품만 있음 | `물품 도착 · {세부 유형}` | 판정 근거 |
  | 그 밖의 방문 | `새 방문 · {상위 분류}` | 요약 (없으면 판정 근거) |
  | `needsReview` | | 끝에 ` (확인 필요)` |

- **언제 보내나:** 방문 처리가 끝났을 때(무응답 판정 직후, 또는 세션 종료 6.4 이후) 한 번. 유예 시간 안에 병합되면 같은 `eventId` 로 한 번 더.
- FCM 이 `404 / UNREGISTERED` 를 돌려주면 그 토큰은 앱이 지워진 것이니 DB 에서 지웁니다.

---

## Spring 으로 옮기기

앱은 고칠 것이 없습니다. 서버 담당이 아래 세 가지만 하면 됩니다.

### 1) 의존성과 키

```gradle
implementation 'com.google.firebase:firebase-admin:9.+'
```

키 파일은 목업과 **같은 파일**(`secrets/firebase-service-account.json`)을 씁니다. compose 의 Spring 서비스에 이미 주석으로 넣어 두었습니다.

```yaml
environment:
  FCM_CREDENTIALS_FILE: /secrets/firebase-service-account.json
volumes:
  - ./secrets:/secrets:ro
```

### 2) 토큰 저장 (11.1)

```sql
CREATE TABLE push_token (
  device_token VARCHAR(512) PRIMARY KEY,
  platform     VARCHAR(16)  NOT NULL,
  created_at   DATETIME     NOT NULL,
  updated_at   DATETIME     NOT NULL
);
```

`POST /api/v1/push-tokens` → 있으면 `updated_at` 만 갱신, 없으면 추가, `201`.

### 3) 발송

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

`title()`·`body()` 는 위 "제목·본문" 표대로 만듭니다.

### 4) 갈아끼우기

1. compose 의 `api` 서비스 `build:` 를 Spring 프로젝트로 바꾸고 위 환경변수·볼륨 주석을 풉니다.
2. `docker compose --profile tunnel up -d --build`
3. 휴대폰 앱은 그대로 `https://api.teamdatacat.com` 에 붙어 있으므로, 앱을 한 번 열면 토큰이 새 서버에 등록됩니다. (목업의 토큰 파일은 옮기지 않아도 됨)
4. `테스트 방문 보내기`는 목업 전용이라 Spring 에서는 "지원하지 않아요"가 뜹니다. 정상입니다.

---

## 아직 안 되는 것

- **알림·응대 정책(분류별 알림 끄기, 방해 금지 시간)** 은 아직 앱 안 알림에만 적용됩니다. 서버가 사용자 정책을 모르기 때문입니다. 정책 API(`VisitPolicy.toJson()` 형식)가 생기면 서버가 보낼지 말지 판단하면 됩니다.
- **아이폰** 은 애플 개발자 계정과 Mac 이 필요해서 이번엔 안드로이드만 합니다.
- **웹(app.teamdatacat.com)** 은 푸시를 받지 않습니다. 화면을 열어 둔 동안 15초마다 새 방문을 확인하는 기존 방식 그대로입니다.
- 사용자 구분(로그인)이 없어서, 등록된 모든 휴대폰에 같은 알림이 갑니다. (API 명세상 인증은 3단계)
