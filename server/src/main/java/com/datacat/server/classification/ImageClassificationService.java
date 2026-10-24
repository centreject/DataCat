package com.datacat.server.classification;

import com.datacat.server.device.DeviceAction;
import com.datacat.server.event.EventStatus;
import com.datacat.server.model.VisionResponse;
import org.springframework.stereotype.Service;

@Service
public class ImageClassificationService {

    public ImageClassificationResult classify(
            String triggerType,
            VisionResponse vision
    ) {
        if (!"TOF".equals(triggerType)
                && !"BUTTON".equals(triggerType)) {
            throw new IllegalArgumentException(
                    "triggerType은 TOF 또는 BUTTON이어야 합니다."
            );
        }

        if (vision == null || vision.detections() == null) {
            throw new IllegalArgumentException(
                    "검증된 이미지 분석 결과가 필요합니다."
            );
        }

        // VisionModelClient에서 검증한 감지 결과를 사용한다.
        int personCount = 0;
        int packageCount = 0;

        for (VisionResponse.Detection detection : vision.detections()) {
            if ("person".equals(detection.label())) {
                personCount++;
            } else if ("package".equals(detection.label())) {
                packageCount++;
            }
        }

        boolean lowVisibility = vision.flags() != null
                && vision.flags().contains("LOW_VISIBILITY");

        // A1: 사람이 보이면 음성 접수를 시작한다.
        if (personCount > 0) {
            String processingStatus = personCount >= 2
                    ? "복수 방문자"
                    : "정상";

            String reason = lowVisibility
                    ? "카메라 가림 상태에서 호출"
                    : "사람 감지 후 음성 접수 시작";

            return reception(
                    "A1",
                    processingStatus,
                    reason,
                    lowVisibility,
                    packageCount
            );
        }

        // A2: 사람이 사진에 없어도 버튼으로 시작했다면 응대한다.
        if ("BUTTON".equals(triggerType)) {
            String reason = lowVisibility
                    ? "카메라 가림 상태에서 호출"
                    : "호출벨로 음성 접수 시작";

            return reception(
                    "A2",
                    "정상",
                    reason,
                    lowVisibility,
                    packageCount
            );
        }

        // A3: 사람이 없고 실제 물품이 감지된 경우다.
        if (packageCount > 0) {
            return standby(
                    "A3",
                    "UNATTENDED_DELIVERY",
                    "물품만 있음",
                    "사람은 감지되지 않았고 물품이 감지되었습니다.",
                    false,
                    packageCount
            );
        }

        // A4: 사람과 물품이 없고 사진을 확인하기 어려운 경우다.
        if (lowVisibility) {
            return standby(
                    "A4",
                    "CAMERA_BLOCKED",
                    "안전 확인 필요",
                    "사진이 잘 보이지 않아 확인이 필요합니다.",
                    true,
                    packageCount
            );
        }

        // A5: 아무것도 없거나 동물만 감지된 경우다.
        return standby(
                "A5",
                "NO_VISITOR",
                "기타·판단 불가",
                "사람과 물품이 감지되지 않았습니다.",
                false,
                packageCount
        );
    }

    // A0: 이미지 모델 호출이 실패했을 때 사용할 판정이다.
    public ImageClassificationResult modelUnavailable() {
        return reception(
                "A0",
                "이미지 판단 실패",
                "이미지 분석 실패, 음성 접수 시작",
                true,
                null
        );
    }

    private ImageClassificationResult reception(
            String ruleId,
            String processingStatus,
            String reason,
            boolean needsReview,
            Integer packageCount
    ) {
        return new ImageClassificationResult(
                ruleId,
                DeviceAction.START_RECEPTION,
                EventStatus.WAITING_AUDIO,
                null,
                null,
                null,
                "일반 접수",
                processingStatus,
                reason,
                needsReview,
                packageCount
        );
    }

    private ImageClassificationResult standby(
            String ruleId,
            String eventType,
            String mainCategory,
            String reason,
            boolean needsReview,
            Integer packageCount
    ) {
        return new ImageClassificationResult(
                ruleId,
                DeviceAction.SILENT_STANDBY,
                EventStatus.COMPLETED,
                eventType,
                mainCategory,
                null,
                "무응답",
                "정상",
                reason,
                needsReview,
                packageCount
        );
    }
}