# DataCat 무인현관 얇은 외형 모델 Rev H

## 핵심 치수

- 완성 외형: **120 × 215 × 50 mm** (가로 × 세로 × 벽면에서 전면까지)
- 이전 Rev G보다 깊이 10 mm 감소
- 외곽 모서리 반경: 34 mm
- 앞면 곡면: 가장자리에서 약 20 mm 구간에 걸쳐 완만하게 상승, 최대 돌출 **6 mm**
- 모델 단위: mm

## 변경 사항

- 본체 깊이 60 mm에서 50 mm로 축소
- 전면 곡면 돌출 10 mm에서 6 mm로 완화
- Raspberry Pi 4, LCD, 카메라, ToF, 버튼, 스피커, 마이크, 앰프 및 전원 배선 공간을 깊이 방향으로 재배치
- 낮아진 전면 곡면에 맞춰 내부 결합 턱과 체결 기둥 높이 조정
- 외부 디자인과 전면 개구부 배치는 유지

## 파일 구성

- `models/01_front_fascia`: 둥근 전면 커버
- `models/02_main_body`: 내부 부품을 담는 본체
- `models/03_rear_plate`: 벽면 쪽 후면판
- `models/04_black_visor`: 카메라·ToF 센서창
- `models/05_control_panel`: 화면·버튼·스피커 홀이 있는 하단 패널
- `models/rounded_enclosure_assembly.obj`: Fusion 조립 확인용 합본
- `models/REFERENCE_ONLY_component_envelopes.obj`: 내부 부품 여유 공간 확인용이며 출력하지 않음

`*_print.stl` 파일은 평평한 면이 출력 베드에 놓이도록 정렬되어 있습니다.

## 내부 여유 공간

- Raspberry Pi 4: 60 × 90 × 24 mm
- 3.5인치 LCD: 64 × 96 × 14 mm
- 카메라: 30 × 25 × 22 mm
- ToF 센서: 16 × 29 × 14 mm
- 버튼: 지름 24 × 깊이 42 mm
- 스피커: 지름 28 × 깊이 24 mm
- 앰프 보드: 22 × 21 × 14 mm
- 마이크 보드: 20 × 16 × 8 mm
- 전원·케이블 공간: 12 × 25 × 22 mm

## 검증 결과

- 5개 출력 부품 모두 watertight 및 winding consistent 통과
- 모든 출력 부품이 각각 하나의 연결된 솔리드인지 확인
- 조립 부품 사이 체적 간섭: 0 mm³
- 내부 부품 여유 공간과 외피 사이 체적 충돌: 0 mm³
- 세부 결과: `validation.json`

## Fusion 360 및 출력 유의사항

1. Fusion에서 OBJ 또는 STL을 불러올 때 단위를 **mm**로 지정합니다.
2. 조립 확인에는 `rounded_enclosure_assembly.obj`를 사용합니다.
3. 실제 구매 부품의 브래킷과 커넥터 위치는 실측 후 최종 고정 기둥에 반영해야 합니다.
4. 프린터에 따라 결합면에 0.2~0.4 mm 공차를 추가할 수 있습니다.
5. 측면 통풍구와 하단 케이블 홈이 있어 현재 구조는 방수형이 아닙니다.
