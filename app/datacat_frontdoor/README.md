# DataCat 현관 앱 (Flutter)

무인현관 기기가 남긴 방문 기록을 확인하는 앱입니다. API 명세 v1.4의 앱 API(9장)와 프리셋 API(10장)를 사용하고, 상황 분류 기획서 17장의 필드(`mainCategory`, `subCategory`, `needsReview` 등)는 서버가 보내기 시작하면 바로 화면에 반영됩니다.

## 처음 실행하기

이 폴더에는 `lib/`, `test/`, `pubspec.yaml`만 있고 플랫폼 폴더(`android/`, `ios/`, `web/`)는 없습니다. 아래 명령으로 만듭니다.

```bash
cd D:\ClaudProject\app\datacat_frontdoor
flutter create . --project-name datacat_frontdoor --platforms=android,ios,web
del test\widget_test.dart      # flutter create가 만드는 기본 테스트. 이 앱과 맞지 않아 지운다
flutter pub get
flutter analyze
flutter test
flutter run -d chrome          # 또는 연결된 안드로이드 기기
```

처음에는 **데모 모드**로 열립니다. 서버 없이 예시 기록 12건으로 모든 화면 상태(정상 접수, 물품만 있음, 확인 필요, 무응답 이탈, 서버 장애)를 볼 수 있습니다.

## 실제 서버에 연결하기

두 가지 방법이 있습니다.

1. 앱의 **설정 → 데모 모드 끄기 → Spring 서버 주소 입력 → 연결 확인 → 저장**
2. 빌드할 때 주소를 지정: `flutter run --dart-define=DATACAT_API=http://192.168.0.12:8080`
   (이렇게 하면 데모 모드가 꺼진 상태로 시작합니다)

주소 끝의 `/api/v1`은 붙여도 되고 빼도 됩니다.

### 개발 중 주의할 것

- **안드로이드에서 `http://` 주소**: 안드로이드 9부터 암호화되지 않은 통신을 막습니다. 개발 중에는 `android/app/src/main/AndroidManifest.xml`의 `<application>` 태그에 `android:usesCleartextTraffic="true"`를 추가하고, `<manifest>` 바로 아래에 `<uses-permission android:name="android.permission.INTERNET"/>`가 있는지 확인하세요. Cloudflare Tunnel(`https://`)을 쓰면 필요 없습니다.
- **크롬(web)으로 실행할 때**: 브라우저의 CORS 정책 때문에 Spring에서 `/api/v1/**`에 대한 CORS를 열어야 목록과 스냅샷 이미지가 보입니다 (`@CrossOrigin` 또는 `WebMvcConfigurer.addCorsMappings`).
- **안드로이드 에뮬레이터**에서 내 PC의 서버는 `localhost`가 아니라 `http://10.0.2.2:8080`입니다.

## 구조

```text
lib/
├─ main.dart              설정을 읽고 앱 시작
├─ app.dart               테마, 전역 상태 연결, 서버 주소가 바뀌면 다시 불러오기
├─ core/
│  ├─ theme.dart          색·간격·모서리 토큰, 라이트/다크 테마
│  └─ format.dart         "오후 10:30", "어제", "3분 전" 같은 한국어 표기
├─ data/
│  ├─ models.dart         VisitEvent, EventPage, Preset (API 9·10장 + 분류 기획 17장)
│  ├─ category.dart       상위 분류 10종과 화면 표현(색, 아이콘, 제목, 현관 그림)
│  ├─ api.dart            DataCatApi 계약과 HTTP 구현, 오류 처리
│  └─ demo_api.dart       서버 없이 쓰는 예시 기록
├─ state/
│  ├─ settings.dart       서버 주소·데모 모드 (기기에 저장)
│  ├─ event_store.dart    방문 목록, 새로고침, 다음 페이지
│  └─ app_scope.dart      위 두 객체를 화면에 내려주는 InheritedWidget
└─ ui/
   ├─ shell.dart          아래 탭 (홈 / 기록 / 설정)
   ├─ home_screen.dart    가장 최근 방문, 오늘 요약, 확인할 것, 최근 기록
   ├─ history_screen.dart 날짜별 기록, 분류 필터, 무한 스크롤
   ├─ event_detail_screen.dart  스냅샷, 남긴 말, 처리 과정, 판정 근거
   ├─ settings_screen.dart      서버 연결, 안내 문구, 개인정보 원칙
   └─ widgets/            배지, 목록 한 줄, 스냅샷, 현관 그림, 빈 화면/오류
```

외부 패키지는 `http`와 `shared_preferences` 두 개뿐입니다. 상태 관리는 Flutter 기본(`ChangeNotifier` + `ListenableBuilder`)으로 했습니다.

## 서버 담당에게 전할 것

- 앱은 `GET /api/v1/events`, `GET /api/v1/events/{id}`, `GET /api/v1/events/{id}/snapshot`, `GET /api/v1/presets`만 호출합니다.
- 목록 응답은 명세의 `{content, page, size, totalElements}`와 Spring Data 기본 형식(`number`, `last`) 둘 다 받습니다.
- 분류 기획의 `mainCategory`(한글 "배송" 또는 `DELIVERY` 같은 코드 모두 가능), `subCategory`, `responsePolicy`, `reason`, `needsReview`를 이벤트 응답에 넣어 주면 화면이 그 값을 우선 사용합니다. 없으면 `eventType` → `purpose` 순서로 분류를 추정합니다.
- 오류 응답 `{code, message}`의 `message`는 사용자에게 그대로 보이니 한국어 문장으로 주세요.

## 아직 안 한 것

- 푸시 알림(FCM, API 11장) — 3단계. `POST /api/v1/push-tokens` 등록과 `event_{id}` 태그 처리가 필요합니다.
- 프리셋 문구 수정 — 기기에 음성 합성이 들어오는 3단계로 미뤄져 있어 앱은 읽기만 합니다.
- 로그인·기기 인증 — 명세상 미구현.
