# 정식 안내 음원 (2026-10-22 민중 청취로 선택)

Pi `raspberry-pi/sounds/`에 이 이름 그대로 복사하면 된다. 16kHz·mono·16bit, Qwen3-TTS 1.7B CustomVoice "Sohee"(Apache 2.0).

| 파일 | 문구 (서버 프리셋과 같음) | 원본 | 말투 지시 |
|---|---|---|---|
| `greeting.wav` | 마이크에 말씀해 주세요. | blind2 `greeting_Y` (1순위) | 경쾌하고 따뜻하게, 조금 높은 음 |
| `greeting_alt.wav` | 〃 | blind2 `greeting_X` (2순위) | 〃 |
| `completion.wav` | 접수되었습니다. | blind2 `completion_Z` ("그나마") | 밝고 미소 띤 안내원처럼 |
| `fallback.wav` | 일시적인 오류로 접수할 수 없습니다. 잠시 후 다시 시도해 주세요. | blind2 `fallback_X` | 경쾌하고 따뜻하게 |

완료 안내 추가 후보: `../blind3/completion_{P,Q,R}.wav` (경쾌한 말투 10개 중 음높이·억양 폭 상위 3개). 더 나은 것이 있으면 `completion.wav`를 바꾼다.
녹음 알림 문구("안녕하세요. 용건을 말씀해 주시면, 집주인에게 전달됩니다.")나 "전달했습니다. 감사합니다."로 정해지면 같은 방식으로 다시 만든다(`../tools/`).
