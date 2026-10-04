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
