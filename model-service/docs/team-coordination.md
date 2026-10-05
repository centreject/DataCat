# AI 담당 팀 협의

> 담당: 김민중(AI 모델) · 마지막 정리: 2026-10-04
> 보내거나 PR을 올리기 전에 민중님이 내용을 확인한다. 보낸 뒤에는 체크하고 날짜를 적는다.
> 지난 초안(인태님 첫 메시지, 명세 v1.4 PR)은 git 기록에 있다(`a98c39f` 이전 버전).

## 할 일

- [ ] **공통 공지** 보내기 — [초안 A](#a-공통-공지)
- [ ] **덕민님 메시지** — [초안 B](#b-덕민님): 용건 9개·우선순위 차이 확인(C4), 요약 문체, 시험 문장, 목업 API 옛 값, compose 모델 블록
- [ ] **인태님 메시지** — [초안 C](#c-인태님): 택배 대체 규칙 합의(C2), 연동 주의사항, 저장소·병합 방식(C1), PR #2 `gradlew`(C9)
- [ ] **수연님 메시지** — [초안 D](#d-수연님): 녹음 형식(16-bit·16kHz·모노)
- [ ] 팀원들께 사진·녹음 요청(C5): 배달 음식 봉지·용기, 보냉백 사진(얼굴 없이) / 현관 앞 실제 녹음 — 민중님이 따로 모아 주시기로 함(Q1)
- [ ] 시연 PC(3090) 관리자: full 프로필 측정(C6). 측정 전까지 시연은 lite
- [ ] **Phase PR** (`feature/ai-model` → main, 명세 v1.5 포함) — C2 합의 후. 본문은 [초안 E](#e-phase-pr)

---

## A. 공통 공지

> [AI 모델] 모델 서비스 명세 **v1.5**를 `feature/ai-model` 브랜치의 `API_v1_5.md`에 올렸습니다. 용건이 덕민님 기획대로 9개가 됐고, 배송 세부 유형(`subtype`), 처리 상태(`flags`), 동물 감지(`animal`)가 추가됐어요.
> GPU 없이 연동을 시험할 수 있는 **가짜 모델 서버**도 만들었습니다: `docker build -f model-service/Dockerfile.mock -t datacat-model-mock model-service` → `docker run -p 8000:8000 datacat-model-mock`. 업로드 파일 이름으로 답을 고릅니다(예: `emergency.wav`, `person_package.jpg`). 응답 예시는 `model-service/docs/examples/`에 있어요.
> 각자 확인 부탁드릴 것은 따로 보내드릴게요.

## B. 덕민님

> 덕민님, 상황 분류 기획서 덕분에 모델 쪽 분류를 9개로 맞췄어요. 확인 부탁드릴 게 있습니다.
>
> 1. **분류 표 확인** — 명세 v1.5 7.6에 용건 9개와 배송 세부 유형 8개가 있어요. 기획서와 다른 곳은 한 곳입니다: **잘못 방문을 배송보다 앞**에 뒀어요. 기획서의 배송 충돌 조건("주소를 잘못 찾았다고 말하면 잘못 방문")을 따르려면 그래야 해서요. 괜찮을까요?
> 2. **요약 문체** — 명사형 20자 이내, 방문객이 말한 낱말만 씁니다(예: "택배 문 앞 보관", "민수 전화 주기"). 말하지 않은 장소·물건이 들어가면 요약 대신 전사문을 그대로 보내고 `SUMMARY_FROM_TRANSCRIPT`를 붙여요. 목업 데이터의 요약("가스 안전점검 재방문 예정")과 같은 방향인데, 앱 화면에 이렇게 보여도 될까요?
> 3. **시험 문장 부탁** — 분류마다 방문객이 할 법한 말을 **5개씩** 써 주시면 정확도를 재는 데만 쓸게요(모델을 그 문장에 맞춰 고치지 않아요). 지금은 기획서 표현과 목업 발화로 만든 64문장을 씁니다.
> 4. **목업 API 값** — `purpose`에 옛 값(`INSPECTION`/`VISIT`/`ETC`)이 남아 있어요(10-05에 추가된 시연용 새 방문 4건 포함). v1.5 값(`SERVICE_VISIT`/`PERSONAL_VISIT`/`UNKNOWN` 등)으로 바꿔 주세요. 참고로 "관리사무소, 아래층 누수 긴급 확인"은 모델도 `PUBLIC_EMERGENCY`로 분류해서 목업의 mainCategory("공공·긴급 방문")와 맞아요.
> 6. **저장소에 크롬 프로필이 올라갔던 것** — `6a161af` 커밋에 `app/datacat_frontdoor/.dart_tool/chrome-device/`(크롬 프로필: Login Data, Cookies 등)가 들어갔다가 `1e6b054`에서 지워졌는데, 저장소가 공개라 **기록에는 남아 있어요.** 파일 크기로 보면 Flutter 웹 디버깅용 빈 프로필 같지만, 그 크롬 창에서 어떤 사이트에 로그인한 적이 있다면 그 사이트 비밀번호 변경·로그아웃을 권해요. 같은 커밋의 `build/`(약 100MB)도 기록에 남아서, main으로 합칠 때는 이 커밋들을 정리(squash)하면 저장소가 가벼워져요.
> 5. **compose 모델 블록** — 서비스 이름 `model` 그대로 좋아요(모델 README도 맞췄습니다). 주석의 healthcheck는 `curl`을 쓰는데 모델 이미지에 curl이 없어서 항상 실패해요 → 그 줄을 빼면 이미지에 든 healthcheck가 쓰입니다. 첫 실행은 가중치 약 10GB를 받으니 `start_period: 3600s`로 해 주세요. GPU 없는 PC에서는 `build: {context: ../model-service, dockerfile: Dockerfile.mock}`으로 가짜 서버를 띄울 수 있어요.

## C. 인태님

> 인태님, 모델 서비스 명세가 v1.5로 바뀌어서 Spring 쪽에 필요한 것만 정리했어요.
>
> 1. **택배 대체 규칙 합의 부탁** — 물품 인식률이 박스 83%, 봉투 80%(목표 85%)라서, Spring에서 **"사람 없음 + ToF 감지 = 물건 도착"**으로도 판단해 주실 수 있을까요? Vision이 `package`를 놓쳐도 배송 알림이 빠지지 않게요.
> 2. **연동할 때 주의할 것**
>    - multipart에 **파일 이름(filename)을 꼭** 넣어 주세요. 없으면 파일로 인식되지 않아 400이 납니다.
>    - 타임아웃: `/audio/process` 4~5초(이 PC 8GB에서 p95 1.5초), `/vision/detect` 1초면 충분해요.
>    - `/health`: `loading`이면 기다리고, `degraded`면 일부 모델만 실패한 상태라 요청은 계속 받아요.
>    - 응답 `flags`가 있으면 "사용자 확인 필요"로 표시하는 걸 권해요. `purpose`는 방문객이 말로 바꿀 수 있어서 출입·보안 판단에는 쓰지 말아 주세요.
>    - 모르는 `label`·`flags` 값이 와도 무시하고 계속 처리하게 해 주세요(값은 명세에 먼저 추가하고 씁니다).
> 3. **저장소 방식** — 각자 브랜치에서 작업하고 Phase가 끝날 때마다 main에 PR로 합치는 방식으로 할게요. 1번 합의되면 `feature/ai-model` PR(명세 v1.5 포함)을 올리겠습니다.
> 4. **PR #2** — `gradlew` 실행 권한 수정(`9f8feb8`) 확인했어요, 100755로 잘 들어갔습니다. 지난 리뷰에 모델 주소를 `http://model-service:8000`이라고 적었는데, 덕민님 compose에 맞춰 **`http://model:8000`**으로 바뀌었어요.
> 5. 모델 서버 없이도 가짜 서버(공통 공지 참고)로 Spring 연동을 먼저 시험해 보실 수 있어요. 파일 이름에 `emergency`를 넣으면 긴급 응답이 와요.

## D. 수연님

> 수연님, Pi에서 음성 보낼 때 형식만 확인 부탁드려요.
>
> - 명세 6.3대로 **WAV, PCM 16-bit, 16kHz, 모노**로 보내 주세요. 다른 형식은 400 `INVALID_AUDIO`가 나요(메시지에 받은 형식이 적혀 와요).
> - INMP441은 보통 32-bit 스테레오로만 열리는데, `plughw` 장치로 녹음하면 arecord가 변환해 줍니다: `arecord -D plughw:<카드>,<장치> -f S16_LE -r 16000 -c 1 visitor.wav`
> - 변환 안 한 파일(48kHz 32-bit 스테레오)은 12배 커서 업로드만으로 타임아웃을 넘길 수 있어요. 음성은 앞 30초만 씁니다.
> - 형식 확인은 가짜 모델 서버에 바로 보내 보면 돼요: `curl -F audio=@visitor.wav http://<PC주소>:8000/internal/v1/audio/process`

## E. Phase PR

**브랜치:** `feature/ai-model` → main · **리뷰어:** 인태님
**PR 제목:** `feat(model-service): 이미지 인식·STT·용건 분류 모델 서비스 + 명세 v1.5`

> AI 모델 서비스(`model-service/`)와 명세 v1.5(`API_v1_5.md`)입니다. 다른 폴더는 건드리지 않았습니다. 명세는 직전 버전 `API_v1_4.md`와 함께 둡니다.
>
> **엔드포인트** (명세 v1.5 7장)
> - `POST /internal/v1/vision/detect` — `person` / `package` / `animal`, `flags`(`LOW_VISIBILITY`)
> - `POST /internal/v1/audio/process` — 전사문 + 용건 9개 + 배송 세부 유형 + 20자 요약 + `flags` (Spring이 쓰는 음성 경로)
> - `POST /internal/v1/speech/transcribe`, `POST /internal/v1/language/analyze` — 단계별
> - `GET /health` — `loading` / `ok` / `degraded` / `error`
>
> **실행**: GPU `docker build -t datacat-model model-service` / GPU 없이 `docker build -f model-service/Dockerfile.mock -t datacat-model-mock model-service`. 확인 `python model-service/docker/smoke.py`.
>
> **측정 (RTX 3060 Ti 8GB, lite)**
> | 항목 | 결과 | 목표 |
> |---|---|---|
> | 음성 처리 전체 p95 | 1.49초 | ≤ 4초 |
> | 용건 정확도 (개발 100문장 / 시험 64문장) | 98% / 98% | ≥ 90% |
> | 긴급·위협 재현율 (개발 / 시험) | 100% / **90%** | ≥ 95% |
> | 배송 세부 유형 (개발 / 시험) | 83% / 86% | ≥ 80% |
> | STT 글자 오류율 (TTS 음성, 잡음 포함) | 3.9–5.3% | ≤ 15% |
> | 사람 / 박스 / 봉투 / 동물 인식 | 93% / 83% / 80% / 97% | 95% / 85% / 85% / 90% — **물품 미달, 팀 사진으로 학습 예정** |
>
> **알아 두실 것**: 시험 문장에서 돌려 말한 위협 1건("가만 안 둬")을 불명으로 분류함 — 보강 예정, 택배 대체 규칙(합의 사항), 음성 앞 30초·업로드 16MB, 음성은 디스크에 쓰지 않음(테스트로 확인), `purpose`로 보안 판단 금지, 컨테이너는 일반 사용자 실행, full 프로필(3090)은 아직 측정 전이라 시연도 lite.
>
> **테스트**: 단위 210개, GPU 35개 통과(사진 없는 2개 건너뜀). 코드 리뷰 3회 반영.
>
> 🤖 Generated with [Claude Code](https://claude.com/claude-code)
