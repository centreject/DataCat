# DataCat 10주차 실장비 통합 시험

Spring과 MySQL을 실제 모델과 함께 RTX 3090 PC에서 실행한다. 같은 네트워크에서 Pi와 휴대폰을 Spring에 연결해 사진 접수부터 음성 처리, 안내 재생, 앱 조회까지 한 방문 번호로 확인한다. 11월 8일은 [API v1.6](../API_v1_6.md)에 적힌 1차 통합 목표일이다. 장비 준비 여부와 실제 일정은 팀에서 확인한다.

## 1. GPU PC에서 서버 준비

기본 Compose에 `docker-compose.server-real.yml`을 더하면 `model` 서비스가 GPU를 쓰는 실제 모델로 바뀐다. Spring은 같은 Docker 네트워크의 `http://model:8000`으로 접근한다. 모델 서비스의 드라이버와 Docker GPU 조건은 [모델 실행 안내](../model-service/README.md)를 따른다. 우선 실측 기록이 있는 `lite`로 실행한다. 가중치 첫 다운로드는 약 10GB이므로 시험 전에 시작한다.

PowerShell에서 저장소의 `datacat-stack` 폴더로 이동한 뒤 아래를 실행한다. 실제 모델 시험의 DB와 사진은 `datacat-week10-real` 프로젝트 볼륨에 따로 저장된다. 같은 PC에서 다른 시험이 이미 18080·13306·18000을 쓰고 있다면 `server.env.example`을 참고해 포트를 바꾸고 아래 URL에도 적용한다.

```powershell
$week10Compose = @('-p', 'datacat-week10-real', '-f', 'docker-compose.server.yml', '-f', 'docker-compose.server-real.yml')
$env:DATACAT_MODEL_BUILD_COMMIT = (git rev-parse --short HEAD).Trim()
docker compose @week10Compose config --quiet
if ($LASTEXITCODE -ne 0) { throw 'Compose 설정을 확인하세요.' }
docker compose @week10Compose up -d --build --wait --wait-timeout 3600
if ($LASTEXITCODE -ne 0) { throw '컨테이너 실행 결과를 확인하세요.' }
docker compose @week10Compose ps
Invoke-RestMethod 'http://localhost:18000/health'
Invoke-RestMethod 'http://localhost:18080/api/v1/presets'
```

모델의 `/health`에서 `status=ok`, `profile=lite`, `build`를 확인한다. `degraded`면 응답의 실패 항목을 모델 담당과 확인한 뒤 결과에 기록한다. 프리셋 조회에서 1번 인사, 2번 완료, 3번 오류 안내를 확인한다. `smoke_server.py run`은 모의 모델용이다. 실제 모델 검증은 아래 실장비 시나리오로 한다.

## 2. Pi와 앱 연결

GPU PC의 `ipconfig`에서 Pi와 같은 네트워크에 연결된 어댑터의 IPv4 주소를 확인한다. Pi에서 `curl --fail http://<GPU_PC_IP>:18080/api/v1/presets`로 먼저 접속한다. 이어서 [Pi 실행 안내](../raspberry-pi/README.md)의 장치 설정을 마친 뒤 Pi의 `raspberry-pi` 폴더에서 아래 명령을 실행한다. `<GPU_PC_IP>`는 실제 주소로 바꾼다.

```bash
.venv/bin/python main.py --server http://<GPU_PC_IP>:18080
```

앱도 같은 서버 루트 주소를 사용하고 데모 모드를 끈다. 푸시까지 시험할 때는 [Firebase 연결 절차](README-server.md#5-android-푸시-후속-시험)의 키 파일 경로를 설정한 뒤 위 PowerShell 배열에 `-f docker-compose.server-fcm.yml`을 추가한다. 같은 배열로 `config --quiet`와 `up -d --wait --wait-timeout 3600`을 다시 실행하고 앱에서 토큰을 등록한다. 조회와 푸시 수신 결과는 따로 적는다.

```powershell
$week10Compose += @('-f', 'docker-compose.server-fcm.yml')
```

## 3. 시연과 회귀 시험

한 대의 Pi로 진행한다. 같은 기기의 요청은 30초 안에 같은 방문으로 합쳐질 수 있으므로 독립 사례를 시작하기 전에 30초를 넘겨 기다리고 Pi가 감시 상태로 복귀했는지 확인한다. 사진과 음원은 시험용으로 준비한다.

| 순서 | 시험 | 통과 기준 |
| --- | --- | --- |
| 1 | 사람이 접근해 택배라고 말한다 | 사진 접수 `START_RECEPTION`. 인사 음원이 끝난 후 녹음. 동일 `eventId`의 `/audio`가 HTTP 200·`PLAY_PRESET` 2번을 반환. 완료 음원 1회, 앱 상세에 배송 분류·전사문·요약·사진 표시 |
| 2 | 방문객이 인사 재생 전 떠난다 | Pi가 `VISITOR_LEFT`로 `/end`를 보냄. `END_SESSION` 및 종료 시각 저장, 녹음 없이 감시 복귀 |
| 3 | 방문객이 안내를 듣고 말하지 않는다 | Pi가 `TIMEOUT`으로 `/end`를 보냄. 종료 기록 저장 및 감시 복귀 |
| 4 | 사진 접수 뒤 모델을 중지하고 음성을 보낸다 | `/audio` 503 또는 Pi 연결 오류 기록, 오류 안내 1회 재생. 모델 정상화 후 새 방문에서 정상 응대 확인 |
| 5 | 성공 음성을 재전송하거나 뒤늦게 종료한다 | 기존 방문 결과 유지. 재분석 및 중복 알림 여부를 각각 확인 |
| 6 | 상자를 그대로 두었다가 치우고 다시 둔다 | 기존 물품으로 반복 알림이 발생하지 않음. 미감지 2회 후 새 도착은 별도 방문 |
| 7 | 휴대폰에서 배송 알림을 열고 서버를 재시작한다 | 알림과 같은 방문의 상세 표시. 서버 재시작 후 같은 방문과 사진 재조회 가능 |

기본값은 Spring 음성 읽기 5초, Pi 요청 대기 10초다. 배송 발화를 여러 번 시험하면서 모델 처리 시간과 Pi가 Spring 응답을 받기까지의 시간을 나눠 기록한다. 모델 로그의 처리 시간과 Pi 측 HTTP 요청 시간을 혼용하지 않는다. 제한을 넘기면 어느 구간이 느린지 확인한 뒤 값을 정한다.

## 4. 제출에 남길 기록

- 시험일, 서버/Pi 커밋, 모델 `/health`의 `profile`·`build`, GPU, 앱 버전, 두 타임아웃 값을 적는다.
- 각 시험은 `eventId`, HTTP 상태, `action`, `presetId`, 처리 시간, 실제 음원과 앱 확인 결과를 적는다. 미실행 항목은 미실행으로 남긴다.
- 시연 영상은 사진 접수, 인사 뒤 발화, 완료 안내, 같은 방문의 앱 상세가 이어지도록 찍는다. 개인 사진·음성, Firebase 키, DB 볼륨은 저장소에 올리지 않는다.

시험을 마치면 같은 PowerShell 창에서 `docker compose @week10Compose stop`으로 중지한다. 이 명령은 방문 기록, 사진, 모델 가중치를 유지한다.
