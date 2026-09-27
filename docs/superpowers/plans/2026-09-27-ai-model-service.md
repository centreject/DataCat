# AI 모델 서비스 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Spring이 호출하는 내부 모델 서비스(이미지 인식 · STT · 요약/용건 분류)를 API v1.3 계약대로 구현하고, 8GB VRAM(lite)과 24GB(full) 양쪽에서 돌아가게 한다.

**Architecture:** 단일 FastAPI 프로세스가 기동 시 세 모델을 로딩한다(`ModelRegistry`). 라우트는 모델 구현체가 아니라 Protocol(`VisionModel`/`SpeechModel`/`LanguageModel`)에만 의존하므로, 단위 테스트는 가짜 모델로 CPU에서 돌고 실제 모델 테스트는 `@pytest.mark.gpu`로 분리한다. 음성은 메모리에서만 처리한다(Zero-Storage).

**Tech Stack:** Python 3.11, FastAPI, pydantic-settings, Ultralytics(YOLO11-pose + YOLOE), faster-whisper, transformers(+bitsandbytes), PyTorch CUDA, pytest, Docker.

**Spec:** `API_v1_3.md` 4장, 7장, 12장, 16장 (모델 서비스 부분). 모델 선정 근거는 팀 대화 정리본을 따른다.

## Global Constraints

- 모든 코드는 `model-service/` 아래에 둔다. `main` 브랜치는 수정하지 않는다. 작업 브랜치는 `feature/ai-model`.
- Base path: `/internal/v1`. 엔드포인트: `POST /vision/detect`, `POST /speech/transcribe`, `POST /language/analyze`, `POST /audio/process`, 추가로 `GET /health`.
- 이미지 입력: `multipart/form-data` 필드 `image`, `image/jpeg`.
- 음성 입력: `multipart/form-data` 필드 `audio`, `audio/wav`, **PCM 16-bit, 16kHz, Mono**. 이외 형식은 400.
- 오류 응답: `{"code": "...", "message": "..."}`. 400 잘못된 요청, 500 내부 오류, 503 모델 사용 불가.
- Vision `label` 허용 값: `person`, `package` (명세의 `box`는 쓰지 않는다 — 인태님께 확정 공유).
- `purpose` 허용 값: `DELIVERY`, `INSPECTION`, `VISIT`, `ETC` (덕민님 승인 전 초안). 목록 밖 값은 `ETC`.
- `summary`: 공백 포함 최대 20자. 초과 시 `s[:19] + "…"` (Spring과 동일 규칙).
- Zero-Storage: 음성 바이트를 디스크(임시 파일 포함)에 쓰지 않는다. 로그에도 전사문 외 음성 데이터를 남기지 않는다.
- 프로필: 환경변수 `MODEL_PROFILE` = `full` | `lite` (기본 `lite`). lite는 8GB VRAM에서 전체 적재가 가능해야 한다.
- uvicorn worker는 1개. 각 모델 래퍼는 추론을 `threading.Lock`으로 직렬화한다(GPU 동시 접근 방지).
- 지연 목표: `/internal/v1/audio/process` p95 ≤ 2.0초(lite, 5초 발화 기준). Pi 타임아웃 3~5초에서 네트워크·Spring 몫을 남기기 위함.

## Review Focus

1. **무음·잡음만 있는 음성** — Whisper가 "시청해 주셔서 감사합니다" 같은 문장을 지어내지 말고 빈 전사(`""`)를 돌려야 한다. → Task 5 필터 테스트, Task 5 GPU 테스트(무음 WAV).
2. **Pi 설정 실수로 온 스테레오/44.1kHz/32-bit WAV** — 크래시가 아니라 400 `INVALID_AUDIO`와 무엇이 틀렸는지 알려주는 메시지. → Task 2.
3. **LLM이 JSON이 아닌 출력, 목록 밖 purpose, 20자 초과 요약을 낼 때** — 규칙 기반 폴백 또는 정규화로 항상 계약에 맞는 응답. → Task 6, Task 7.
4. **모델 로딩 중에 들어온 요청** — 503 `MODEL_NOT_READY`, 서버는 죽지 않음. → Task 1.
5. **등을 돌린 사람 / 화면 끝에 잘린 사람(떠나는 택배 기사)** — `person`은 감지하되 `facingCamera: false`. → Task 3.

---

## 파일 구조

```text
model-service/
├─ pyproject.toml            # 의존성, pytest 설정(gpu 마커)
├─ README.md                 # 실행법, 프로필, API 차이점(bbox/facingCamera 제안)
├─ Dockerfile
├─ app/
│  ├─ main.py                # create_app(), lifespan, 라우터 등록
│  ├─ config.py              # Settings, 프로필별 모델 설정
│  ├─ errors.py              # ApiError + 핸들러
│  ├─ schemas.py             # 요청/응답 pydantic 모델
│  ├─ protocols.py           # VisionModel / SpeechModel / LanguageModel
│  ├─ registry.py            # ModelRegistry, load_registry(settings)
│  ├─ media.py               # decode_jpeg, decode_wav (메모리 전용)
│  ├─ pipeline.py            # analyze_transcript, process_audio
│  ├─ routes.py              # 5개 엔드포인트
│  ├─ vision/pose.py         # is_facing_camera
│  ├─ vision/yolo.py         # YoloVision
│  ├─ speech/filters.py      # clean_segments
│  ├─ speech/whisper.py      # WhisperSpeech
│  ├─ language/normalize.py  # truncate_summary, parse_llm_output
│  ├─ language/rules.py      # rule_analyze
│  └─ language/qwen.py       # QwenLanguage, build_messages
├─ tests/                    # 단위(가짜 모델) + gpu 마커 통합 테스트
│  └─ fixtures/              # 샘플 jpg/wav (Task 2에서 생성 스크립트로 만듦)
├─ bench/benchmark.py        # VRAM·지연 측정
└─ eval/                     # 정확도 평가 스크립트 + 라벨 데이터
```

---

### Task 0: 개발 환경 준비 (이 PC: RTX 3060 Ti 8GB, Python·Docker 미설치)

**Files:** 없음 (로컬 환경)

- [ ] **Step 1:** Python 3.11 설치 — `winget install Python.Python.3.11`. 확인: `py -3.11 --version` → `Python 3.11.x`
- [ ] **Step 2:** `model-service/.venv` 생성 후 CUDA PyTorch 설치 — `pip install torch --index-url https://download.pytorch.org/whl/cu124`. 확인: `python -c "import torch;print(torch.cuda.is_available())"` → `True`
- [ ] **Step 3:** Docker Desktop(WSL2 백엔드) 설치 — Task 11 전까지만 끝내면 된다. 확인: `docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi` 에 3060 Ti 표시.

---

### Task 1: 서비스 뼈대 — 설정, 오류 형식, 레지스트리, `/health`

**Files:**
- Create: `model-service/pyproject.toml`, `app/main.py`, `app/config.py`, `app/errors.py`, `app/protocols.py`, `app/registry.py`, `app/schemas.py`, `app/routes.py`
- Test: `tests/test_app.py`, `tests/conftest.py`

**Interfaces:**
- Produces:
  - `Settings(BaseSettings)`: `model_profile: Literal["full","lite"]="lite"`, `person_conf: float=0.4`, `package_conf: float=0.3`, `keypoint_conf: float=0.5`, `stt_model: str="large-v3-turbo"`, `llm_model: str="Qwen/Qwen3-4B-Instruct-2507"`, `llm_max_new_tokens: int=64`. 프로필 파생값은 프로퍼티: `stt_compute_type` (`full`→`"float16"`, `lite`→`"int8_float16"`), `llm_quantize_4bit` (`lite`→`True`).
  - `ApiError(status: int, code: str, message: str)`; `install_error_handlers(app)`. 코드: `INVALID_IMAGE`(400), `INVALID_AUDIO`(400), `INVALID_REQUEST`(400), `MODEL_NOT_READY`(503), `INFERENCE_FAILED`(500). FastAPI 검증 오류도 `INVALID_REQUEST` 형식으로 변환.
  - `protocols.py`: `VisionModel.detect(image: PIL.Image.Image) -> list[Detection]`, `SpeechModel.transcribe(audio: np.ndarray) -> str` (float32, 16kHz), `LanguageModel.analyze(transcript: str) -> Analysis`.
  - `schemas.py`: `Detection(label: Literal["person","package"], confidence: float, bbox: list[float] | None = None, facingCamera: bool | None = None)` — bbox는 `[x1,y1,x2,y2]` 0~1 정규화, `DetectResponse(detections: list[Detection])`, `TranscribeResponse(transcript: str)`, `AnalyzeRequest(transcript: str)`, `Analysis(summary: str, purpose: Literal["DELIVERY","INSPECTION","VISIT","ETC"])`, `AudioProcessResponse(transcript: str, purpose: str, summary: str)`.
  - `ModelRegistry` dataclass: `vision`, `stt`, `language` (각각 Optional), `ready: bool`. `load_registry(settings) -> ModelRegistry` (실제 모델은 Task 4·5·7에서 채움; 이 태스크에선 빈 레지스트리).
  - `create_app(registry_factory: Callable[[Settings], ModelRegistry] = load_registry) -> FastAPI` — lifespan에서 팩토리를 **백그라운드 스레드**로 실행해 로딩 중에도 `/health`가 응답하게 한다. `app.state.registry`에 저장.
  - `routes.py`: `require(registry, name) -> model` — 준비 안 됐으면 `ApiError(503,"MODEL_NOT_READY",...)`.

- [ ] **Step 1: 실패하는 테스트 작성** (`tests/test_app.py`)
  - `test_health_reports_loading_then_ok`: 팩토리가 `threading.Event`를 기다리게 한 앱 → `GET /health` = `{"status":"loading","profile":"lite"}`; 이벤트 set 후 → `{"status":"ok","profile":"lite"}`.
  - `test_detect_while_loading_returns_503`: 로딩 중 `POST /internal/v1/vision/detect` → 503, 본문 `{"code":"MODEL_NOT_READY","message":...}`.
  - `test_validation_error_uses_error_format`: `POST /internal/v1/language/analyze` 본문 `{}` → 400, `code == "INVALID_REQUEST"`.
  - `test_profile_derived_settings`: `Settings(model_profile="full").stt_compute_type == "float16"`, `Settings().llm_quantize_4bit is True`.
- [ ] **Step 2:** `pytest tests/test_app.py -v` → FAIL (모듈 없음)
- [ ] **Step 3:** 위 Interfaces대로 구현. `pyproject.toml`에 `[tool.pytest.ini_options] markers = ["gpu: needs CUDA and real weights"]`, 기본 `addopts = "-m 'not gpu'"`.
- [ ] **Step 4:** `pytest -v` → PASS
- [ ] **Step 5:** Commit — `feat(model-service): app skeleton, error format, health, profiles`

---

### Task 2: 입력 디코딩 — JPEG, WAV(메모리 전용)

**Files:**
- Create: `app/media.py`, `tests/fixtures/make_fixtures.py`
- Test: `tests/test_media.py`

**Interfaces:**
- Produces: `decode_jpeg(data: bytes) -> PIL.Image.Image` (RGB), `decode_wav(data: bytes) -> np.ndarray` (float32, [-1,1], 1차원). 표준 라이브러리 `wave` + `io.BytesIO`만 사용.
- `make_fixtures.py`: `tone_wav(seconds, rate=16000, channels=1, sampwidth=2) -> bytes`, `silence_wav(seconds) -> bytes`, `tiny_jpeg() -> bytes` — 테스트에서 import해서 씀(파일 커밋 불필요).

- [ ] **Step 1: 실패하는 테스트 작성**
  - `test_decode_wav_ok`: 1초 16k mono 16-bit → `shape == (16000,)`, `dtype == float32`, `abs().max() <= 1.0`.
  - `test_decode_wav_rejects_stereo` / `_rejects_44100` / `_rejects_32bit`: 각각 `ApiError` status 400, code `INVALID_AUDIO`, message에 각각 `"mono"`, `"16000"`, `"16-bit"` 포함.
  - `test_decode_wav_rejects_garbage`: `b"not a wav"` → `INVALID_AUDIO`.
  - `test_decode_wav_rejects_empty`: 0프레임 WAV → `INVALID_AUDIO`.
  - `test_decode_jpeg_ok` / `test_decode_jpeg_rejects_png`: PNG 바이트 → `INVALID_IMAGE`.
- [ ] **Step 2:** `pytest tests/test_media.py -v` → FAIL
- [ ] **Step 3:** 구현. JPEG는 `Image.open(...).format == "JPEG"` 확인 후 `.convert("RGB")`.
- [ ] **Step 4:** `pytest -v` → PASS
- [ ] **Step 5:** Commit — `feat(model-service): in-memory JPEG/WAV decoding with validation`

---

### Task 3: `/vision/detect` 라우트 + 정면 판정 (가짜 모델로)

**Files:**
- Create: `app/vision/pose.py`
- Modify: `app/routes.py`
- Test: `tests/test_vision.py`

**Interfaces:**
- Consumes: `decode_jpeg`, `require`, `DetectResponse`.
- Produces: `is_facing_camera(keypoints: np.ndarray, min_conf: float) -> bool` — `keypoints` shape `(17,3)` COCO 순서 `(x,y,conf)`. 코(0)의 conf ≥ min_conf **그리고** 왼눈(1) 또는 오른눈(2)의 conf ≥ min_conf 이면 `True`.

- [ ] **Step 1: 실패하는 테스트 작성**
  - `test_facing_when_nose_and_eye_visible` → True.
  - `test_not_facing_when_back_turned`: 코·눈 conf 0.1, 어깨만 0.9 → False.
  - `test_not_facing_when_only_nose`: 코 0.9, 두 눈 0.2 → False.
  - `test_detect_route_returns_contract`: 가짜 VisionModel이 `[Detection(label="person", confidence=0.94, bbox=[0.1,0.2,0.5,0.9], facingCamera=False)]` 반환 → 응답 JSON `detections[0]` 이 그대로, `label`/`confidence` 키 존재.
  - `test_detect_route_empty`: 가짜가 `[]` → `{"detections": []}`.
  - `test_detect_route_rejects_non_jpeg` → 400 `INVALID_IMAGE`.
- [ ] **Step 2:** `pytest tests/test_vision.py -v` → FAIL
- [ ] **Step 3:** 구현. 라우트는 `response_model_exclude_none=True`로 선택 필드가 없으면 생략.
- [ ] **Step 4:** `pytest -v` → PASS
- [ ] **Step 5:** Commit — `feat(model-service): vision detect endpoint and facing-camera rule`

---

### Task 4: 실제 비전 모델 `YoloVision` (Phase 1 마감 대상)

**Files:**
- Create: `app/vision/yolo.py`
- Modify: `app/registry.py` (`load_registry`가 vision 로딩)
- Test: `tests/test_vision_gpu.py` (`@pytest.mark.gpu`)

**Interfaces:**
- Consumes: `VisionModel`, `Detection`, `is_facing_camera`, `Settings`.
- Produces: `YoloVision(settings: Settings)` implements `VisionModel`.
  - 사람: `yolo11s-pose.pt` — 박스(`person`) + 키포인트 → `facingCamera`. `conf >= settings.person_conf`.
  - 택배: `yoloe-11s-seg.pt`(open-vocabulary)에 `set_classes(["cardboard box", "parcel", "package"])` → 모두 `package`로 매핑. `conf >= settings.package_conf`. 파인튜닝 가중치가 생기면 설정값 `package_weights`로 교체(후속 계획).
  - bbox는 이미지 크기로 나눠 0~1 정규화, 소수 4자리 반올림. 추론 fp16, `threading.Lock`으로 직렬화.

- [ ] **Step 1: 실패하는 GPU 테스트 작성** — 테스트 이미지는 `tests/fixtures/images/`에 팀이 직접 찍은 사진(초상권 문제 없는 팀원 사진)으로 추가.
  - `test_person_facing.jpg` → `person` 1개 이상, `facingCamera is True`.
  - `test_person_back.jpg` → `person`, `facingCamera is False`.
  - `test_package_only.jpg` → `package` 있음, `person` 없음.
  - `test_empty_hallway.jpg` → `detections == []`.
- [ ] **Step 2:** `pytest -m gpu tests/test_vision_gpu.py -v` → FAIL
- [ ] **Step 3:** 구현.
- [ ] **Step 4:** `pytest -m gpu tests/test_vision_gpu.py -v` → PASS. 실패하는 사진이 있으면 임계값을 조정하고 조정값을 `Settings` 기본값에 반영.
- [ ] **Step 5:** Commit — `feat(model-service): YOLO11-pose + YOLOE package detector`
- [ ] **Step 6:** 인태님께 공유 — 엔드포인트 동작 확인용 `curl -F image=@x.jpg http://localhost:8000/internal/v1/vision/detect` 예시, `label`은 `package`, 선택 필드 `bbox`/`facingCamera` 추가 제안(명세 7.1 수정 요청).

---

### Task 5: STT — 환각 필터, `/speech/transcribe`, `WhisperSpeech`

**Files:**
- Create: `app/speech/filters.py`, `app/speech/whisper.py`
- Modify: `app/routes.py`, `app/registry.py`
- Test: `tests/test_speech.py`, `tests/test_speech_gpu.py`

**Interfaces:**
- Consumes: `decode_wav`, `SpeechModel`, `TranscribeResponse`.
- Produces:
  - `clean_segments(segments: Iterable[tuple[str, float]], max_no_speech_prob: float = 0.6) -> str` — `(text, no_speech_prob)`. no_speech_prob 초과 세그먼트와 `HALLUCINATION_PHRASES`(최소: `"시청해 주셔서 감사합니다"`, `"시청해주셔서 감사합니다"`, `"구독과 좋아요"`, `"MBC 뉴스"`)를 포함하는 세그먼트를 버리고 공백 하나로 이어 `strip()`.
  - `WhisperSpeech(settings)` — `faster_whisper.WhisperModel(settings.stt_model, device="cuda", compute_type=settings.stt_compute_type)`. `transcribe(audio)` 호출 인자: `language="ko"`, `beam_size=1`, `vad_filter=True`, `condition_on_previous_text=False`, `initial_prompt="택배, 배달, 배송, 검침, 점검, 관리사무소, 방문"`. 결과를 `clean_segments`에 통과.

- [ ] **Step 1: 실패하는 테스트 작성**
  - `test_clean_drops_hallucination`: `[("택배 왔습니다", 0.1), ("시청해 주셔서 감사합니다", 0.2)]` → `"택배 왔습니다"`.
  - `test_clean_drops_high_no_speech`: `[("음", 0.9)]` → `""`.
  - `test_transcribe_route`: 가짜 SpeechModel이 `"택배 왔습니다."` → `{"transcript": "택배 왔습니다."}`.
  - `test_transcribe_route_rejects_stereo` → 400 `INVALID_AUDIO`.
  - GPU: `test_silence_gives_empty` — 3초 무음 → `""`. `test_korean_sample` — `tests/fixtures/audio/delivery_01.wav`(팀원 녹음, INMP441로 녹음한 것이 이상적) → `"택배"` 포함.
- [ ] **Step 2:** `pytest tests/test_speech.py -v` → FAIL
- [ ] **Step 3:** 구현.
- [ ] **Step 4:** `pytest -v` 그리고 `pytest -m gpu tests/test_speech_gpu.py -v` → PASS
- [ ] **Step 5:** Commit — `feat(model-service): faster-whisper STT with hallucination filter`

---

### Task 6: 언어 — 정규화, 규칙 폴백, `/language/analyze`

**Files:**
- Create: `app/language/normalize.py`, `app/language/rules.py`, `app/pipeline.py`
- Modify: `app/routes.py`
- Test: `tests/test_language.py`

**Interfaces:**
- Consumes: `Analysis`, `AnalyzeRequest`, `LanguageModel`.
- Produces:
  - `truncate_summary(s: str, limit: int = 20) -> str` — `strip()` 후 `len > limit`이면 `s[:limit-1] + "…"`.
  - `parse_llm_output(raw: str) -> Analysis | None` — 첫 `{`~마지막 `}` 구간을 JSON 파싱. 실패하거나 `summary`가 비었으면 `None`. `purpose`는 대문자화, 목록 밖이면 `ETC`. `summary`는 `truncate_summary`.
  - `rule_analyze(transcript: str) -> Analysis` — 키워드 우선순위 DELIVERY > INSPECTION > VISIT, 없으면 ETC. 키워드: DELIVERY `택배, 배달, 배송, 소포, 음식, 물건`; INSPECTION `검침, 점검, 관리사무소, 관리실, 가스, 소독, 수리, 설치, 공사`; VISIT `친구, 나야, 엄마, 아빠, 언니, 오빠, 형, 누나, 놀러`. summary는 `truncate_summary(transcript)`.
  - `analyze_transcript(model: LanguageModel, transcript: str) -> Analysis` — 빈 전사(공백만 포함) → `Analysis(summary="용건 인식 실패", purpose="ETC")`, 모델을 부르지 않음. 모델 예외 → `rule_analyze`.

- [ ] **Step 1: 실패하는 테스트 작성**
  - `test_truncate_exact_20_kept`, `test_truncate_21_becomes_19_plus_ellipsis` (결과 길이 20, 끝 `"…"`).
  - `test_parse_valid`, `test_parse_with_surrounding_text` (`"결과: {...} 입니다"`), `test_parse_garbage_none`, `test_parse_unknown_purpose_is_etc` (`"purpose":"FOOD"` → `ETC`), `test_parse_lowercase_purpose` (`"delivery"` → `DELIVERY`).
  - `test_rules_delivery`: `"택배 문 앞에 두고 갑니다"` → `DELIVERY`. `test_rules_inspection`: `"가스 검침 왔습니다"` → `INSPECTION`. `test_rules_etc`: `"안녕하세요"` → `ETC`.
  - `test_empty_transcript_skips_model`: 호출되면 실패하는 가짜 모델 + `"  "` → `summary == "용건 인식 실패"`.
  - `test_model_exception_falls_back_to_rules`.
  - `test_analyze_route_contract`: 응답 키가 정확히 `{"summary","purpose"}`.
- [ ] **Step 2:** `pytest tests/test_language.py -v` → FAIL
- [ ] **Step 3:** 구현.
- [ ] **Step 4:** `pytest -v` → PASS
- [ ] **Step 5:** Commit — `feat(model-service): language normalize, rule fallback, analyze endpoint`

---

### Task 7: 실제 sLM `QwenLanguage`

**Files:**
- Create: `app/language/qwen.py`
- Modify: `app/registry.py`
- Test: `tests/test_qwen.py`, `tests/test_qwen_gpu.py`

**Interfaces:**
- Consumes: `parse_llm_output`, `rule_analyze`, `Settings`.
- Produces:
  - `build_messages(transcript: str) -> list[dict]` — system 프롬프트(역할, purpose 정의 4개, "summary는 공백 포함 20자 이내 명사형", "JSON 한 줄만 출력"), few-shot 4개(용건별 1개), user = transcript.
  - `QwenLanguage(settings)` implements `LanguageModel` — `AutoModelForCausalLM`, `settings.llm_quantize_4bit`이면 `BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=torch.float16)`, 아니면 `torch_dtype=torch.bfloat16`. greedy(`do_sample=False`), `max_new_tokens=settings.llm_max_new_tokens`. `parse_llm_output` 결과가 `None`이면 `rule_analyze`.

- [ ] **Step 1: 실패하는 테스트 작성**
  - `test_build_messages_contains_all_purposes`: system 내용에 네 값 모두 포함, 마지막 메시지가 `{"role":"user","content": transcript}`.
  - GPU: `test_qwen_delivery` — `"택배 왔습니다. 문 앞에 놓고 갈게요."` → `purpose == "DELIVERY"`, `len(summary) <= 20`. `test_qwen_inspection` — `"관리사무소에서 소방 점검 나왔습니다"` → `INSPECTION`.
- [ ] **Step 2:** `pytest tests/test_qwen.py -v` → FAIL
- [ ] **Step 3:** 구현.
- [ ] **Step 4:** `pytest -v` 그리고 `MODEL_PROFILE=lite pytest -m gpu tests/test_qwen_gpu.py -v` → PASS
- [ ] **Step 5:** Commit — `feat(model-service): Qwen3 analyzer with 4bit lite profile`

---

### Task 8: `/audio/process` 통합 + Zero-Storage 검증

**Files:**
- Modify: `app/pipeline.py`, `app/routes.py`
- Test: `tests/test_audio_process.py`

**Interfaces:**
- Consumes: `decode_wav`, `SpeechModel`, `analyze_transcript`.
- Produces: `process_audio(registry: ModelRegistry, wav: bytes) -> AudioProcessResponse` — decode → transcribe → analyze. 중간 결과를 반환하지 않는다.

- [ ] **Step 1: 실패하는 테스트 작성**
  - `test_process_audio_contract`: 가짜 STT `"택배 문 앞에 두고 갑니다."`, 가짜 LM `Analysis("택배 문 앞 보관","DELIVERY")` → 응답이 정확히 `{"transcript","purpose","summary"}`.
  - `test_process_audio_silence`: 가짜 STT `""` → `summary == "용건 인식 실패"`, `purpose == "ETC"`.
  - `test_process_audio_writes_no_files`: `tempfile.mkstemp`, `tempfile.NamedTemporaryFile`, `tempfile.SpooledTemporaryFile`을 호출 시 예외를 던지게 monkeypatch + `tmp_path`를 cwd로 둔 상태에서 요청 → 200, 요청 전후 `tempfile.gettempdir()`와 cwd 파일 목록 동일. (Starlette 업로드가 1MB 이하 WAV를 메모리에 유지함을 이 테스트로 함께 고정; 5초 16k 16-bit ≈ 160KB.)
  - `test_process_audio_stt_not_ready` → 503.
- [ ] **Step 2:** `pytest tests/test_audio_process.py -v` → FAIL
- [ ] **Step 3:** 구현.
- [ ] **Step 4:** `pytest -v` → PASS
- [ ] **Step 5:** Commit — `feat(model-service): audio process endpoint with zero-storage guarantee`

---

### Task 9: 벤치마크 — VRAM·지연 (8GB 가능 여부 판정)

**Files:**
- Create: `bench/benchmark.py`, `bench/results/.gitkeep`

**Interfaces:**
- Consumes: `load_registry`, `Settings`, `process_audio`, fixture 생성 함수.
- Produces: CLI `python bench/benchmark.py --profile lite --runs 20` → stdout 마크다운 표 + `bench/results/<GPU이름>_<profile>.json`. 항목: GPU 이름, 총 VRAM, 모델별 로딩 후 `torch.cuda.max_memory_allocated`와 `nvidia-smi` 사용량, 로딩 시간, vision/stt/language/audio-process 각 p50·p95(ms). 첫 1회는 워밍업으로 제외.

- [ ] **Step 1:** 구현 후 `python bench/benchmark.py --profile lite --runs 3` 스모크 실행 → 표 출력, JSON 생성.
- [ ] **Step 2:** 이 PC(3060 Ti 8GB)에서 `--profile lite --runs 20` 실행. 판정: 로딩 성공 + audio-process p95 ≤ 2000ms. 실패 시 `llm_model`을 `Qwen/Qwen3-1.7B`로 바꿔 재측정하고 lite 기본값을 결과에 맞게 수정.
- [ ] **Step 3:** `--profile full`은 시연 PC(3090)에서 실행하도록 README에 명시. 결과 JSON을 커밋.
- [ ] **Step 4:** Commit — `perf(model-service): VRAM/latency benchmark and 3060Ti lite results`

---

### Task 10: 정확도 평가 스크립트 + 초기 평가셋

**Files:**
- Create: `eval/purpose_cases.jsonl`, `eval/eval_language.py`, `eval/eval_stt.py`, `eval/eval_vision.py`, `eval/README.md`

**Interfaces:**
- `purpose_cases.jsonl`: 한 줄에 `{"transcript": str, "purpose": str}`. 초기 40건(용건별 10건, 구어체·말줄임·잡음 섞인 표현 포함). 덕민님 분류 기획이 확정되면 100건으로 확장.
- `eval_language.py` → 전체 정확도, 용건별 precision/recall, 혼동 행렬, 20자 초과 비율(0이어야 함), 폴백 발생 비율.
- `eval_stt.py` → `eval/audio/*.wav` + 같은 이름 `.txt` 정답으로 CER(공백 제거 후 문자 편집거리 / 정답 길이).
- `eval_vision.py` → `eval/images/<label폴더>/`별 person·package 감지 정밀도/재현율, facingCamera 정확도.

- [ ] **Step 1:** 스크립트 구현, `eval_language.py`를 규칙 전용(`--rules-only`)으로 실행해 동작 확인.
- [ ] **Step 2:** lite 프로필로 Qwen 평가 실행, 결과를 `eval/README.md`에 기록(날짜, 모델, 정확도).
- [ ] **Step 3:** Commit — `test(model-service): accuracy evaluation harness and seed dataset`

---

### Task 11: Docker 이미지 + 통합 안내

**Files:**
- Create: `model-service/Dockerfile`, `model-service/.dockerignore`, `model-service/README.md`

**Interfaces:**
- Dockerfile: `nvidia/cuda:12.4.1-cudnn-runtime-ubuntu22.04` 기반, Python 3.11, 가중치는 이미지에 굽지 않고 볼륨 `/models`(`HF_HOME`, Ultralytics 가중치 경로)에 캐시. `CMD uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8000 --workers 1`. `HEALTHCHECK`는 `/health`가 `ok`일 때 성공.
- README: 실행법(venv / Docker), `MODEL_PROFILE`, 엔드포인트 curl 예시, **API v1.3 대비 제안 사항**(label `package` 확정, `bbox`/`facingCamera` 선택 필드, `/health`), 인태님 compose에 넣을 서비스 블록 예시(`gpus: all`, 포트 8000, 볼륨).

- [ ] **Step 1:** `docker build -t datacat-model model-service` → 성공.
- [ ] **Step 2:** `docker run --rm --gpus all -e MODEL_PROFILE=lite -p 8000:8000 -v datacat-models:/models datacat-model` 후 `/health`가 `ok`가 될 때까지 대기 → 네 엔드포인트 curl 스모크 통과.
- [ ] **Step 3:** Commit — `build(model-service): CUDA Dockerfile and integration README`

---

## 이 계획 밖의 후속 작업 (별도 계획으로)

- 택배 전용 YOLO11 파인튜닝: 실제 마운트 각도로 촬영한 데이터와 공개 택배 데이터셋 수집 → 학습 → Task 10 비전 평가로 YOLOE 대비 개선 확인 → `package_weights` 교체.
- `purpose` 최종 목록 확정(덕민님) 시 `Analysis.purpose`, 프롬프트, 규칙, 평가셋을 함께 갱신.
- STT·LLM 모델 교체 비교(예: Whisper large-v3, EXAONE, Qwen3-8B 4bit)는 Task 9·10 도구로 같은 조건에서 측정.

## 팀 일정과의 연결

| 팀 Phase | 필요한 태스크 |
|---|---|
| Phase 1 (이미지 흐름, 2~3주) | Task 0 → 1 → 2 → 3 → 4, 그리고 11을 앞당겨 실행(인태님 compose 연동용, 스모크는 `/health`·`/vision/detect`만) |
| Phase 2 (음성 흐름, 4~5주) | Task 5 → 6 → 7 → 8 → 9 → 10 |
