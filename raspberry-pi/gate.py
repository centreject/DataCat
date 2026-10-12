"""재확인 게이트(명세 v1.5 5.3). 프리셋 재생 직전 방문객이 아직 있는지 로컬에서 판단한다."""

import time

GATE_ATTEMPTS = 5
GATE_INTERVAL = 0.06


def visitor_present(read_distance, release_cm, attempts=GATE_ATTEMPTS,
                    interval=GATE_INTERVAL, sleep=time.sleep):
    """해제 거리 안쪽 값이 유효 측정의 과반이면 True.

    유효 측정이 하나도 없으면 이탈로 본다. 측정 실패가 계속될 때
    사람이 남아 있다고 판단해 아무도 없는 현관에 안내를 재생하지 않기 위해서다.
    """
    near = valid = 0
    for i in range(attempts):
        if i:
            sleep(interval)
        distance = read_distance()
        if distance is None:
            continue
        valid += 1
        if distance < release_cm:
            near += 1
    return valid > 0 and near * 2 > valid
