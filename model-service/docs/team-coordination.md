# AI 담당 팀 협의 할 일 목록

> 작성: 2026-09-27 · 담당: 김민중(AI 모델)
> 보내거나 PR을 올리기 전에 민중님이 내용을 확인한다. 보낸 뒤에는 체크하고 날짜를 적는다.

## 할 일

- [ ] **인태님 메시지 전달** — 아래 [초안 1](#초안-1-인태님께-보낼-메시지)
- [ ] **API 명세 PR 올리기** (`API_v1_3.md`만 수정하는 작은 PR) — 아래 [초안 2](#초안-2-api-명세-pr)
- [ ] 인태님과 합의: 택배 대체 규칙("사람 없음 + ToF 감지" = 물건 도착) — 초안 1에 포함
- [ ] 덕민님: `purpose` 4개 값(`DELIVERY`/`INSPECTION`/`VISIT`/`ETC`) 승인, 요약 문체 예시 5개 확인 — 요약에 말하지 않은 단어만 있으면 전사문을 대신 보여 주는 규칙도 확인(예: "엄마, 나야" → "가족 방문" 대신 원문)
- [ ] 팀원들께 사진 요청: 배달 음식 봉지·용기, 보냉백(프레시백) — 문 앞 바닥에 놓인 모습, 얼굴 없이
- [ ] 시연 PC(3090) 관리자: Task 9·10 끝나면 `bench/benchmark.py --profile full`, `eval/*` 실행 요청
- [ ] Phase 2 초반: 인태님·덕민님께 `facingCamera`/`bbox` 선택 필드 제안 (떠나는 택배 기사 대응)

---

## 초안 1. 인태님께 보낼 메시지

> 인태님, AI 모델 쪽 Phase 1(이미지 인식) 1차 구현이 끝나서 공유드립니다. 확인 부탁드릴 게 4가지 있어요.
>
> **1. 저장소·브랜치 방식 제안**
> - 저장소 하나에 파트별 폴더: `spring-server/`, `model-service/`, `pi/`, `app/`
> - 각자 자기 브랜치에서 작업하고, **Phase가 끝날 때마다** main에 PR로 병합 (Phase 1 끝, Phase 2 끝)
> - 루트 `docker-compose.yml`은 인태님이 관리해 주시고, 모델 서비스 블록은 제가 PR로 제안드릴게요
> - 제 작업은 `feature/ai-model` 브랜치, `model-service/` 폴더에 있습니다
>
> **2. 이미지 인식 엔드포인트 (지금 동작함)**
> - `POST /internal/v1/vision/detect` (multipart `image`, JPEG)
> - 응답: `{"detections":[{"label":"person","confidence":0.94},{"label":"package","confidence":0.61}]}`
> - `label`은 `person` / `package` 두 가지만 씁니다 (명세의 `box`는 안 씀)
> - `GET /health` → `{"status":"loading|ok|error","profile":"lite|full"}` — 모델 로딩 중에는 다른 요청에 503 `MODEL_NOT_READY`
> - 오류는 전부 명세 12장 `{code, message}` 형식입니다
> - 포트는 8000으로 생각하고 있어요. Docker 이미지는 곧 올리겠습니다
>
> **3. 택배 인식률이 아직 낮아서 대체 규칙 합의가 필요해요**
> - 공개 이미지로 잰 인식률: 사람 93%, 택배 박스 53%, 비닐봉투 72% (목표 사람 95%, 택배 85%)
> - 학습 없이 쓰는 모델이라 그렇고, 팀 사진이 모이면 택배 전용으로 학습해서 올릴 예정입니다
> - 그때까지 Spring에서 **"사람 없음 + ToF 감지 = 물건 도착"** 으로도 판단해 주실 수 있을까요? Vision이 package를 못 잡아도 배송 알림이 빠지지 않게요
>
> **4. 명세 수정 PR 올릴게요**
> - label 확정, 발화 없을 때 응답 규칙, `/health` 추가, 모델 서비스 오류 코드 목록 — 명세만 고치는 작은 PR이라 리뷰 부탁드립니다
>
> 테스트는 이렇게 해보실 수 있어요: `curl -F image=@door.jpg http://localhost:8000/internal/v1/vision/detect`

---

## 초안 2. API 명세 PR

**브랜치:** `docs/api-model-service` (main에서 분기) · **대상:** main · **리뷰어:** 인태님
**PR 제목:** `docs(api): 모델 서비스 응답 규칙 확정 (label, 빈 전사, /health, 오류 코드)`

### PR 본문

> 모델 서비스(AI) 구현 과정에서 확정된 내용을 명세에 반영합니다. 모델 서비스 부분(7장, 12장, 16장)만 바뀌고 Pi·앱 API는 그대로입니다.
>
> **변경 사항**
> 1. **7.1 이미지 인식** — `label` 허용 값을 `person`, `package`로 확정(`box` 삭제). `package` 범위: 택배 박스, 비닐 택배봉투, 배달 음식 봉지·용기, 보냉백. 사람이 들고 있는 물건도 `package`로 나올 수 있음(구분하지 않음).
> 2. **7.2~7.4 발화 없음** — 전사 결과가 비면 `transcript=""`, `summary=""`, `purpose="ETC"`. 알림 문구는 Spring·앱이 `transcript`가 비었는지 보고 정한다.
> 3. **7.3 요약 문체** — 명사형(예: `택배 문 앞 보관`), 공백 포함 20자 이내. *(덕민님 확인 대기)*
> 4. **7.5 신규: 상태 확인** — `GET /health` → `{"status": "loading" | "ok" | "error", "profile": "lite" | "full"}`. 로딩 중·실패 시 추론 요청은 503 `MODEL_NOT_READY`.
> 5. **12장 오류 코드(모델 서비스)** — `INVALID_IMAGE`(400), `INVALID_AUDIO`(400), `INVALID_REQUEST`(400), `NOT_FOUND`(404), `METHOD_NOT_ALLOWED`(405), `MODEL_NOT_READY`(503), `INFERENCE_FAILED`(500).
> 6. **16장 TBD 4** — 모델 서비스 포트 `8000` 제안 (Docker 서비스 이름은 compose 확정 시).
>
> **바뀌지 않는 것:** 엔드포인트 경로, 요청 형식(JPEG / WAV PCM 16-bit·16kHz·mono), 응답 필드 이름.
>
> 🤖 Generated with [Claude Code](https://claude.com/claude-code)

### 명세에 넣을 문구 (변경 위치별)

**7.1 필드 설명 표의 `label` 행**
> | `label` | String | 인식된 항목. 허용 값: `person`, `package`. `package`는 택배 박스, 비닐 택배봉투, 배달 음식 봉지·용기, 보냉백을 모두 포함한다. 사람이 들고 있는 물건도 `package`로 나올 수 있다. |

**7.4 아래 참고 블록 추가**
> **발화가 없을 때**: 전사 결과가 비어 있으면(무음·잡음만 녹음된 경우) `{"transcript": "", "purpose": "ETC", "summary": ""}`를 반환한다. 표시 문구는 Spring·앱이 정한다.

**7.5 신규 섹션**
> ## 7.5 모델 서비스 상태 확인
> `GET /health` (서비스 루트 경로. `/internal/v1` 아래가 아님)
> 응답: `{"status": "loading", "profile": "lite"}` — `status`는 `loading`(모델 로딩 중) / `ok` / `error`(로딩 실패). `loading`·`error` 상태에서 추론 요청은 503 `MODEL_NOT_READY`를 받는다. Docker healthcheck와 Spring 기동 순서 확인에 사용한다.

**12장 표 아래 추가**
> 모델 서비스 오류 코드: `INVALID_IMAGE`(400, JPEG 아님/깨짐), `INVALID_AUDIO`(400, WAV 형식 불일치 — 메시지에 받은 형식과 필요한 형식을 함께 적음), `INVALID_REQUEST`(400), `NOT_FOUND`(404), `METHOD_NOT_ALLOWED`(405), `MODEL_NOT_READY`(503), `INFERENCE_FAILED`(500).

**변경 이력 행**
> | `v1.4` | (병합일) | 모델 서비스: `label` 값 확정(`person`/`package`)과 package 범위, 빈 전사 응답 규칙, 요약 문체, `GET /health`, 모델 서비스 오류 코드 목록, 포트 8000 제안 |
