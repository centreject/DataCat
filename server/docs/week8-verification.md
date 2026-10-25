# 팀플 8주차 서버 검증 기록

기록일: 2026-10-25. 담당: 조인태(Spring 서버).
수동 검증은 2026-10-24~25 한국 시간에 진행했다.
아래 eventId는 로컬 DB의 시험 번호이며 다른 환경에서 동일할 필요는 없다.

## 검증 환경과 범위

| 구분 | 환경·의미 |
|---|---|
| Spring | Windows IntelliJ, Java 21, Spring Boot 4.1.1, 포트 8080 |
| DB | 로컬 MySQL 8.0.46, datacat, DBeaver로 상태 확인 |
| 모델 | Docker의 datacat-model-mock, 포트 8000, /health profile=mock |
| Pi 요청 대체 | PowerShell curl.exe로 JPEG·JSON·WAV 전송 |
| 자동 테스트 | H2 기반 서비스·MockMvc·모의 HTTP 테스트 |
| 앱 | Android APK. 새 로컬 주소로 토큰 재등록·알림 갱신 재시험 대기 |

person.jpg는 생성한 시험 이미지다. package·empty 사진도 같은 바이트를 다른 이름으로 복사해 모의 모델 분기를 선택했다.
delivery.wav는 PCM 16-bit·16kHz·mono, 1초 무음, 32,044바이트다.
모의 모델은 파일 이름으로 준비된 결과를 반환하므로 무음 파일에서도 예시 배송 전사문이 나온다.
이 결과는 실제 STT·이미지 인식 정확도의 근거가 아니다.

## 자동 테스트

Java 21 검증 환경의 XML 결과: 총 145개, 실패 0, 오류 0, 건너뜀 0.
같은 구현 파일을 적용한 Windows에서도 최종 gradlew.bat test의 BUILD SUCCESSFUL을 확인했다.

| 테스트 클래스 | 개수 |
|---|---:|
| ServerApplicationTests | 1 |
| AudioClassificationServiceTests | 32 |
| EndClassificationServiceTests | 6 |
| DeviceEventServiceTests | 7 |
| DevicePackageImageTests | 13 |
| DeviceSessionAudioTests | 29 |
| DeviceSessionEndTests | 11 |
| PackageReceptionServiceTests | 7 |
| EventImageStateTests | 4 |
| AudioModelClientTests | 22 |
| PushTokenRegistrationTests | 6 |
| VisitPushServiceTests | 7 |
| 합계 | 145 |

주요 범위는 판정표 B/C, 모델 응답 검사, 음성 재전송, 상태 충돌, DB 롤백, 커밋 후 푸시,
물품 상태와 파일 정리, 동시 분석 실패다. 실제 Firebase 전달·Pi 음원 재생을 모의 시험으로 대신 검증한 것은 아니다.
일부 deprecated API 경고와 JVM 공유 경고가 있었으나 빌드는 성공했다.

## 수동 검증 결과

| 사례 | 요청·조건 | 관측 결과 |
|---|---|---|
| 12 | 음성 대기 방문에 VISITOR_LEFT 종료 | 200, COMPLETED, END_SESSION. VISITOR_TIMEOUT·기타·판단 불가·안내 전 이탈 저장 |
| 13 | 새 방문에 delivery.wav 업로드 | 200, COMPLETED, PLAY_PRESET 2. DELIVERY·배송·택배·전사문·요약 저장 |
| 13 재전송 | 모델을 중지하고 마지막 성공 녹음을 다시 전송 | 200 기존 응답. 전사문·요약·endedAt 동일 |
| 14 장애 | 정상 사진 뒤 모델을 중지하고 첫 음성 전송 | 503 MODEL_SERVICE_UNAVAILABLE. WAITING_AUDIO, 분석 결과·endedAt null 유지 |
| 14 복구 | 모델 재시작·health 200 후 같은 방문에 재전송 | 200, COMPLETED. DELIVERY 분석 결과 저장 |
| 14 늦은 종료 | 음성 성공 후 VISITOR_LEFT 종료 요청 | 200 END_SESSION. 기존 eventType·purpose·전사문·요약·endedAt 유지 |
| 12 늦은 음성 | 음성 없이 종료된 방문에 WAV 전송 | 409 EVENT_STATE_CONFLICT |
| 15 첫 물품 | 새 기기의 TOF·package 사진 | 201, COMPLETED, SILENT_STANDBY. 물품 상태 presence=1, missCount=0 |
| 15 재감지 | 35초 대기 후 같은 기기로 package 사진 | 200, 같은 eventId 15. 30초 이후에도 재알림 대상 새 방문을 만들지 않음 |
| 16 첫 미감지 | 같은 기기로 empty 사진 | 201, COMPLETED. 물품 상태 유지, missCount=1, packageEventId=15 |
| 17 두 번째 미감지 | 같은 기기로 empty 사진 재요청 | 201, COMPLETED. 물품 상태 행 0건, 과거 Event 15는 1건 유지 |
| 18 재도착 | 상태 해제 후 package 사진 | 201, 새 eventId 18. presence=1, missCount=0, packageEventId=18 |
| 19 사진 실패 | 모델 중지 상태에서 새 BUTTON·사진 요청 | 201, WAITING_AUDIO, START_RECEPTION. 이미지 판단 실패·needsReview=true |
| 19 음성도 실패 | 모델을 계속 중지한 상태에서 WAV 전송 | 503. 조회는 200이며 오류 종료가 DB에 저장됨 |

사진·음성 장애 시험의 finally 블록에서 모의 모델을 다시 시작했다.
사진·물품 상태의 컬럼 추가와 저장을 실제 MySQL에서 확인했다. 기존 기록을 삭제해서 통과시킨 시험이 아니다.

### 음성 결과 예시 — 로컬 13·14번

- purpose: DELIVERY
- transcript: 택배 왔습니다. 문 앞에 놓고 갈게요.
- summary: 택배 문 앞 보관
- mainCategory / subCategory: 배송 / 택배
- responsePolicy / processingStatus: 일반 접수 / 정상
- reason: 용건: 배송(택배)
- needsReview: false

### 동시 실패 결과 — 로컬 19번

| 필드 | 관측 값 |
|---|---|
| HTTP 음성 요청 | 503 MODEL_SERVICE_UNAVAILABLE |
| HTTP 상세 조회 | 200 |
| status | COMPLETED |
| eventType | VISITOR_TIMEOUT |
| mainCategory | 기타·판단 불가 |
| responsePolicy | 장애 안내 |
| processingStatus | 이미지 판단 실패 |
| reason | 이미지·음성 분석 실패 |
| needsReview | true |
| purpose / transcript / summary | null |
| endedAt | 저장됨 |

COMPLETED는 접수 종료이며 분석 성공을 뜻하지 않는다.
음성 전 조회의 WAITING_AUDIO와 음성 실패 뒤의 COMPLETED는 서로 다른 시점의 결과다.
PowerShell이 이전 표 출력을 뒤늦게 표시한 순서와 최종 DB 상태를 혼동하지 않는다.

`기타·판단 불가` 종료 방향은 판정표 A0를 따른다.
VISITOR_TIMEOUT 재사용·장애 안내·오류 reason 조합과 오류 완료 후 음성 409는 구현 제안이며 팀 확인 대상이다.
자세한 조건은 [동시 실패 처리](model-failure-handling.md)를 따른다.

## 표시·도구 관련 확인

- UTF-8 JSON을 curl.exe의 -o로 저장하고 Get-Content -Raw -Encoding UTF8로 읽어 한글을 확인했다.
- curl의 한글 -w 표시가 깨진 경우에도 JSON 원문·저장 값은 정상으로 확인했다. 다음 시험에는 ASCII 라벨을 사용한다.
- DBeaver의 새 컬럼 밑줄과 실제 SQL 실행 성공을 구분했다. 필요하면 테이블 메타데이터를 새로 고친다.
- DBeaver 표시 시각과 API +09:00 출력만으로 모델 실행 시간을 계산하지 않는다.
- 단계 사이에 수동 작업·Docker 시작/중지가 있어 이 로그는 추론 지연 측정 자료가 아니다.

## 앱·Pi·실제 모델 확인 대기

7주차에는 Android 기본 푸시 수신과 알림 상세 이동을 확인했다.
8주차 앱은 로컬 서버 주소를 저장한 뒤에도 푸시 등록 표시가 이전 공용 서버에 남아 있었다.
로컬 push_token 조회에서도 기존 등록 시각이 10-21로 남아 새 주소 등록을 확인하지 못했다.
알림을 받은 사실만으로 앱 조회·토큰 등록·발송 서버가 모두 같은 서버라고 판단하지 않는다.

아래 항목은 이번 주 로컬 시험의 완료 범위에 포함하지 않는다.

1. 앱 주소 변경 후 로컬 서버 토큰 등록, 음성 결과로 같은 알림 교체, 해당 방문 상세 이동.
2. 현재 브랜치의 실제 Pi 사진·음성·종료 송수신, 프리셋 2번과 503 오류 음원 3번 재생.
3. 실제 Vision·STT·용건 모델의 정확도·처리 시간과 타임아웃 조정.
4. 현재 Spring 변경을 포함한 전체 Docker 실행 구성 재현.

하드웨어 담당이 이전 서버로 확인한 연결과 현재 변경을 반영한 재시험은 구분한다.
2차 사진 업로드·선택 종료 사진 multipart·서버 만료 타이머는 미구현이다.
재전송 ID·새 방문 경계·동시 실패 세부 값 등 TBD는 [API 명세 16장](../../API_v1_5.md)에 정리한다.
