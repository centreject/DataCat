# 서버 Docker 통합 시험

기준: main c681ace, PR #9 병합 이후. 2026-10-28.

## 구성과 출처

feature/app-design의 datacat-stack (db99369)의 api/db/model 구성과 MySQL 8.4·사진 Volume 설계를 바탕으로 한다. 현재 main에 Flutter 앱 폴더가 없으므로 `docker-compose.server.yml` 하나로 서버 세 부분을 먼저 실행한다. 기존 앱용 docker-compose.yml 및 docker-compose.spring.yml과 함께 합쳐 실행하는 파일이 아니다. 향후 앱 브랜치 통합 때 이 서버 구성을 앱 스택에 연결한다.

| 서비스 | 호스트에서 접근 | 컨테이너 간 주소 | 저장 |
|---|---|---|---|
| Spring | http://localhost:18080 | http://api:8080 | spring-snapshots Volume |
| MySQL 8.4 | 127.0.0.1:13306 | db:3306 | db-data Volume |
| 모의 모델 | http://localhost:18000 | http://model:8000 | 시험용, 모델 가중치 불필요 |

Compose 프로젝트 이름은 datacat-week9다. 기존 단독 datacat-model-mock과 httpd 컨테이너를 사용하거나 삭제하지 않는다. 로컬 MySQL과 별도 DB여서 기존 방문 21·22번 등이 새 목록에 나타나지 않는 것이 정상이다. 기존 DB 기록을 지우거나 이동하지 않는다.

## 1. 실행

Docker Desktop이 준비된 뒤 PowerShell에서 한 줄씩 실행한다. 기존 IntelliJ 서버와 로컬 MySQL은 이 구성의 실행에 필요하지 않다.

```powershell
cd C:\springproject\DataCat\datacat-stack
docker compose -f docker-compose.server.yml config --quiet
docker compose -f docker-compose.server.yml up -d --build --wait --wait-timeout 300
docker compose -f docker-compose.server.yml ps
curl.exe -i "http://localhost:18080/api/v1/presets"
curl.exe -i "http://localhost:18000/health"
```

최초 실행에는 Java·Python·MySQL 이미지와 Gradle·Python 의존성 다운로드가 필요하다. 빌드 중 로그가 길어도 최종 성공/오류를 확인한다. `api`, `db`, `model`이 모두 healthy이고, 프리셋 HTTP 200과 모델 health의 profile=mock이면 준비 완료다.

서버 Dockerfile은 Java 21로 bootJar를 만든다. 테스트는 이미지에 포함하지 않으며, 빌드에서는 기존 자동 테스트를 다시 돌리지 않는다. 실제 컨테이너 검증은 아래 절차로 한다. DB는 실제 DB 사용자로 SELECT 1이 성공해야 healthy, Spring은 방문 조회 API가 성공해야 healthy다.

## 2. 사진·음성·종료 API 시험

아래 스크립트는 모델 컨테이너에 이미 있는 Python·Pillow를 사용한다. PC에 Python을 설치하지 않아도 된다. 합성 JPEG·무음 WAV를 전송하고 파일 이름으로 정해진 모의 결과를 받는다. 실제 인식 정확도 시험은 아니다. 시험 실행마다 방문 2개가 새로 생성된다.

```powershell
$smokeResult = docker compose -f docker-compose.server.yml exec -T model python /opt/datacat-tests/smoke_server.py run
if ($LASTEXITCODE -ne 0) { throw "통합 시험이 실패했습니다. 표시된 FAIL 내용을 확인해 주세요." }
$smokeResult

$dockerEvidenceDir = "C:\springproject\datacat-test-files"
[System.IO.Directory]::CreateDirectory($dockerEvidenceDir) | Out-Null
$dockerEvidencePath = Join-Path $dockerEvidenceDir "week9-docker-smoke.json"
[System.IO.File]::WriteAllText($dockerEvidencePath, ($smokeResult -join "`n"), [System.Text.UTF8Encoding]::new($false))
```

정상 결과는 JSON의 `result: PASS`다. 프리셋 조회, 사진 접수 201, 동일 방문 음성 접수 200·PLAY_PRESET·2번, 배송 상세·전사문·사진 조회, 같은 녹음 재전송의 응답 유지, 별도 방문의 /end를 확인한다. 이 스크립트는 푸시 수신·실제 음원 재생·재분석 횟수까지 입증하지 않는다.

## 3. 컨테이너 재생성 뒤 기록·사진 유지

2번의 PASS 기록 파일을 저장한 후 진행한다. 아래 `down`에는 Volume 삭제 옵션을 붙이지 않는다.

```powershell
docker compose -f docker-compose.server.yml down
docker compose -f docker-compose.server.yml up -d --wait --wait-timeout 300
Get-Content -LiteralPath "C:\springproject\datacat-test-files\week9-docker-smoke.json" -Raw | docker compose -f docker-compose.server.yml exec -T model python /opt/datacat-tests/smoke_server.py verify
```

`result: PASS`, `check: database-and-snapshot-persistence`면 저장했던 방문 번호·배송 결과·종료 기록·사진 SHA-256이 유지된 것이다. 2번 run을 다시 실행하는 것은 새 방문 생성이므로 기존 기록 유지 검증을 대신하지 않는다.

## 4. 종료·다음 실행·문제 확인

```powershell
# 컨테이너만 중지
docker compose -f docker-compose.server.yml stop
# 다음 실행
docker compose -f docker-compose.server.yml up -d --wait --wait-timeout 300
# 문제 확인
docker compose -f docker-compose.server.yml logs --tail 80 api db model
```

로그를 공유할 때 개인 사진·전사문·비밀번호·서비스 계정 파일을 붙이지 않는다. 포트 충돌이면 server.env.example을 `.env`로 복사해서 DATACAT_TEST_*_PORT를 바꾸고 접속 URL도 맞춘다. DB 비밀번호 변경은 기존 Volume의 DB 사용자 비밀번호를 자동 변경하지 않는다. 처음 만든 DB 비밀번호를 유지하거나 DB 사용자 설정을 함께 변경한다.

## 5. Android 푸시 후속 시험

기본 구성은 FCM_ENABLED=false다. 컨테이너 통합·영속성 확인 후 기존 Firebase 서비스 계정 파일을 읽기 전용으로 연결한다.

```powershell
$env:DATACAT_TEST_FCM_KEY_FILE = "C:/springproject/datacat-secrets/firebase-service-account.json"
Test-Path $env:DATACAT_TEST_FCM_KEY_FILE
docker compose -f docker-compose.server.yml -f docker-compose.server-fcm.yml config --quiet
docker compose -f docker-compose.server.yml -f docker-compose.server-fcm.yml up -d --wait --wait-timeout 300
```

Test-Path가 True일 때만 진행한다. 앱의 서버 주소를 `http://PC의IPv4주소:18080`으로 바꾸고 데모 모드를 끈 뒤 새 서버에 푸시 토큰을 재등록한다. 새 DB에는 기존 IntelliJ 서버에 등록했던 토큰이 없으므로 재등록이 필요하다. PC와 휴대폰의 네트워크 연결도 확인한다.

FCM을 켠 상태의 이후 up/stop 명령에는 두 -f 파일을 함께 사용한다. 기본 파일만으로 다시 up하면 FCM이 꺼진 구성으로 돌아간다. 실제 수신·같은 방문 알림 갱신·상세 일치·중복 알림 여부는 휴대폰에서 관찰한다.

## 검증 범위

- Compose v5.5.1로 기본 파일과 FCM overlay의 config 검사 통과. 기본 api/db/model 세 서비스, 서로 다른 호스트 포트, DB·사진 Volume, FCM 키와 사진 Volume의 공존을 확인했다.
- Python 시험 스크립트 문법 검사 완료. 실제 실행 결과는 함께 제공하는 검증 기록을 따른다.
- Java 21의 Spring 실행 JAR·모의 모델·임시 H2 파일 DB로 위 시험 스크립트의 run과 서버 재시작 후 verify가 모두 PASS였다. 이 결과는 HTTP 흐름과 시험 스크립트 검증이며, Docker의 MySQL·Volume 검증은 1~3번으로 진행한다.
- 사용자 PC의 Docker 이미지 빌드·MySQL·Volume 재생성 시험은 위 명령으로 확인해야 한다. 파일 전달만으로 Docker 실행 완료로 기록하지 않는다.
- 실제 Pi·실제 모델·스피커 재생은 별도 단계다. 이번 구성은 모의 모델만 사용한다.

참고: https://docs.docker.com/compose/how-tos/startup-order/ · https://docs.docker.com/compose/how-tos/project-name/
