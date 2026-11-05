# datacat-stack — 도커로 한 번에 띄우기

Flutter 앱(웹)과 API 서버를 도커로 묶은 것입니다. 팀원 PC에서도, 서버 PC에서도 같은 명령으로 돌아갑니다.

```text
브라우저 ──▶ app (nginx :8081) ──/api/──▶ api (:8080) ──▶ db (MySQL, Spring 붙일 때)
                                          ▲
Raspberry Pi ─────────────────────────────┘ (http://서버IP:8080/api/v1/...)
```

지금 `api`는 **목업 서버**입니다. API 명세 v1.4대로 예시 방문 기록 12건을 돌려줍니다. Spring Boot가 준비되면 `docker-compose.yml`의 `api.build` 한 줄만 바꾸면 됩니다.

## 실행

준비물: Docker Desktop(Windows/Mac) 또는 Docker Engine(Linux). Flutter 설치는 필요 없습니다.

```bash
cd datacat-stack
docker compose up -d --build     # 처음엔 Flutter 이미지를 받느라 5~15분
```

| 확인 | 주소 |
|---|---|
| 앱 | http://localhost:8081 |
| API | http://localhost:8080/api/v1/events |
| 상태 | http://localhost:8080/health |

같은 와이파이의 휴대폰이나 다른 PC에서는 `localhost` 대신 이 컴퓨터의 IP를 씁니다(Windows: `ipconfig`의 IPv4 주소).

자주 쓰는 명령:

```bash
docker compose logs -f api       # 로그 보기
docker compose down              # 끄기 (DB 데이터는 남음)
docker compose up -d --build     # 코드 바꾼 뒤 다시 띄우기
```

## 시연용 새 방문

목업 API는 `MOCK_AUTO_VISIT_SECONDS`(기본 180초)마다 새 방문을 하나씩 만들어요. 앱이 15초마다 확인하니, 켜 두면 "새 방문" 알림 띠가 뜨는 걸 볼 수 있어요. 바로 만들고 싶으면:

```bash
curl -X POST http://localhost:8090/api/v1/_mock/visits      # 포트는 .env 의 API_PORT
```

끄려면 `.env`에 `MOCK_AUTO_VISIT_SECONDS=0`을 넣어요.

사람이 온 방문은 실제 서버처럼 먼저 "응대 중"(WAITING_AUDIO)으로 보였다가, `MOCK_RECEPTION_SECONDS`(기본 20초) 뒤에 음성 결과가 나온 것처럼 분류가 채워져요. 푸시도 같은 알림이 내용만 바뀌어요. 분류 값은 저장소의 `판정표.md`를 따라요.

## Spring 서버로 테스트

목업 API 대신 서버 담당이 만든 Spring 서버를 띄워서 앱을 붙여 볼 수 있어요. 앱은 고칠 필요 없어요.

Spring 코드와 모델 서비스가 아직 다른 브랜치에 있어서, 처음 한 번은 따로 받아 둬야 해요.

```powershell
git clone -b feature/image-upload https://github.com/centreject/DataCat.git C:\DataCat-spring
git clone -b main https://github.com/centreject/DataCat.git C:\DataCat-main
```

`.env`에 두 경로를 적어요.

```
SPRING_DIR=C:/DataCat-spring/server
MODEL_DIR=C:/DataCat-main/model-service
```

실행 (MySQL과 모의 모델 서비스가 같이 떠요. 처음엔 Gradle 빌드 때문에 몇 분 걸려요)

```powershell
docker compose -f docker-compose.yml -f docker-compose.spring.yml --profile backend --profile tunnel up -d --build
```

- 앱 화면은 그대로 `app.teamdatacat.com`(또는 `localhost:APP_PORT`)에서 봐요. dev 프로필이라 처음엔 예시 방문 3건이 보여요.
- 라즈베리파이 대신 사진을 올려 보려면 `.\pi-sim.ps1`을 실행해요. `-Kind package`, `-Kind empty`, `-Trigger BUTTON`으로 경우를 바꿀 수 있어요.
- Spring에는 아직 푸시 토큰 등록과 목업 전용 기능이 없어서, 앱 설정의 푸시 칸은 "등록하지 못했어요", 테스트 방문 보내기는 "지원하지 않아요"로 나와요.
- 팀원 코드가 바뀌면 `git -C C:\DataCat-spring pull`, `git -C C:\DataCat-main pull` 후 같은 명령으로 다시 띄워요.

목업으로 돌아갈 때

```powershell
docker compose --profile tunnel up -d --build --remove-orphans
```

나중에 Spring과 모델 서비스가 main에 합쳐지고 이 브랜치도 main을 따라가면, 따로 받은 폴더 없이 `git pull` 후 위 실행 명령만 쓰면 돼요.

## 휴대폰 푸시 알림

새 방문이 생기면 안드로이드 앱으로 푸시를 보냅니다. Firebase 키를 `secrets/` 에 넣으면 켜지고, 없으면 꺼진 채로 서버만 뜹니다.
안드로이드 앱은 `build-apk.ps1`(윈도우) / `build-apk.sh` 로 도커에서 빌드합니다. 순서와 Spring 이관 방법은 **[PUSH.md](PUSH.md)**.

## 프로필

| 명령 | 추가로 뜨는 것 |
|---|---|
| `docker compose --profile backend up -d` | MySQL 8.4 (데이터는 `db-data` 볼륨에 보존) |
| `docker compose --profile tunnel up -d` | Cloudflare Tunnel — 집 밖에서 HTTPS로 접속 |
| (모델 서버) | `model` 서비스 주석을 풀고 `--profile gpu` |

## Spring Boot로 바꾸기 (백엔드 담당)

1. Spring 프로젝트 폴더에 Dockerfile을 둡니다. 포트는 8080입니다.
2. `docker-compose.yml`의 `api.build: ./mock-api`를 Spring 폴더 경로로 바꾸고, 주석에 있는 `environment`를 풉니다.
3. `docker compose --profile backend up -d --build`

앱은 그대로 둡니다. nginx가 `/api/`를 `api` 서비스로 넘기기 때문입니다.

## 서버 PC에 배포

1. 이 폴더와 `app/datacat_frontdoor`가 **같은 상대 위치**로 있도록 저장소를 clone합니다(`../app/datacat_frontdoor`).
2. `cp .env.example .env` 후 DB 비밀번호를 바꿉니다.
3. Linux: `./deploy.sh` / Windows: `docker compose up -d --build`
4. 업데이트할 때도 같은 명령을 다시 실행합니다.

`restart: unless-stopped`가 걸려 있어서 서버 PC를 재부팅해도 도커가 켜지면 자동으로 다시 뜹니다.

## 문제 해결

| 증상 | 해결 |
|---|---|
| `port is already allocated` | `.env`의 `APP_PORT`나 `API_PORT`를 바꿉니다. |
| app 빌드 중 `pub get` 실패 (Flutter 버전) | `pubspec.lock`이 요구하는 버전보다 이미지가 오래된 경우입니다. compose의 `app.build.args`에 `FLUTTER_IMAGE: ghcr.io/cirruslabs/flutter:<버전>`을 추가합니다. |
| 앱은 뜨는데 기록이 없음 | 설정 탭에서 데모 모드가 켜져 있거나 예전 주소가 저장된 경우입니다. 시크릿 창으로 열어 보세요. |
| Pi가 접속 못 함 | 서버 PC 방화벽에서 8080 포트를 허용합니다. |
