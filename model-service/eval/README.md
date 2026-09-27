# 평가 (정확도)

모두 `model-service/`에서 실행한다. 데이터는 `data/`(git 제외)에 만들어진다.

| 준비 | 명령 |
|---|---|
| 공개 이미지 받기 | `python eval/prepare_images.py` |
| TTS 평가 음성 만들기 | `python -m eval.make_tts_audio` |

| 평가 | 명령 |
|---|---|
| 용건 분류 (규칙만) | `python -m eval.eval_language --rules-only` |
| 용건 분류 (LLM) | `python -m eval.eval_language` |
| STT | `python -m eval.eval_stt` |
| 이미지 인식 | `python -m eval.eval_vision` |

프로필은 환경변수 `MODEL_PROFILE=lite|full`로 고른다. 목표치는 [`metrics.py`](metrics.py)의 `TARGETS`(계획 문서의 잠정 목표, full 기준).

## 데이터

- **용건 평가셋** [`purpose_cases.jsonl`](purpose_cases.jsonl): 40건, 용건별 10건. 반례 포함("택배 아니고요, 관리실에서…", "정수기 렌탈 홍보" vs "정수기 필터 교체"). 덕민님 분류 기획이 확정되면 100건으로 늘린다.
- **STT 음성**: 위 40문장을 edge-tts(남·여 음성 번갈아)로 합성. `tts/` 원본, `tts_snr20/`·`tts_snr10/` 백색 잡음 추가. 실제 INMP441 녹음은 `data/audio/real/<id>.wav` + `<id>.txt`로 넣으면 같이 평가된다.
- **이미지**: Open Images 검증·테스트 세트 일부. 배달 음식·보냉백은 공개 데이터가 없어 팀 사진이 필요하다.

## 결과 기록

### 2026-09-27 · lite 프로필 · RTX 3060 Ti 8GB

**STT** — `large-v3-turbo`, `int8_float16`

| 음성 | 파일 수 | 평균 CER | 목표 ≤ 15% |
|---|---:|---:|---|
| TTS 원본 | 40 | 3.8% | PASS |
| TTS + 잡음 20dB | 40 | 4.2% | PASS |
| TTS + 잡음 10dB | 40 | 5.6% | PASS |

가장 많이 틀린 문장: "로켓프레시 보냉백" → "로켓프렛이 본행백" (CER 25–31%). TTS는 실제 마이크 녹음보다 쉬운 조건이므로 실제 녹음으로 다시 잰다.

**용건 분류 — 규칙만(LLM 실패 시 대체용)**: 정확도 52% (목표 90% FAIL), 요약 20자 초과 0%. 키워드에 없는 표현(쿠팡, 등기, 치킨, 보일러, 할머니 등)은 대부분 ETC로 분류된다. LLM이 필요한 이유이며, 규칙 보강은 평가셋과 겹치지 않는 문장으로 따로 한다.

**용건 분류 — LLM**: 아직 측정 못 함. PyTorch가 Qwen 실행 중 Triton 커널을 컴파일하는데 C 컴파일러가 없음(`sudo apt install -y build-essential`).

**이미지 인식** — person_conf 0.4, package_conf 0.25

| 폴더 | 이미지 수 | 찾은 비율 | 목표 |
|---|---:|---:|---|
| person | 30 | 93% | ≥ 95% FAIL |
| package_box | 30 | 53% | ≥ 85% FAIL |
| package_bag | 25 | 72% | ≥ 85% FAIL |
| package_food / package_cooler | 0 | — | 팀 사진 필요 |
| empty (오탐) | 30 | 7% | 낮을수록 좋음 |

### full 프로필 (시연 PC, 3090)

아직 없음 — 시연 PC 관리자에게 실행 요청 예정.
