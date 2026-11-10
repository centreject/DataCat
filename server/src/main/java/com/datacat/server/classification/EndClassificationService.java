package com.datacat.server.classification;

import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;

@Service
public class EndClassificationService {

    public EndClassificationResult classify(String endReason, int maxPackageCount) {
        if (maxPackageCount < 0) {
            throw new IllegalArgumentException("세션 사진의 최대 물품 수는 0 이상이어야 합니다.");
        }
        return classify(endReason, maxPackageCount > 0);
    }

    public EndClassificationResult classify(String endReason, boolean hasPackage) {
        if (!"VISITOR_LEFT".equals(endReason) && !"TIMEOUT".equals(endReason)
                && !"DEVICE_CANCELLED".equals(endReason)) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST,
                    "reason은 VISITOR_LEFT, TIMEOUT 또는 DEVICE_CANCELLED이어야 합니다.");
        }
        if ("DEVICE_CANCELLED".equals(endReason)) {
            return interrupted(hasPackage, "단말에서 장치 오류로 응대를 중단함");
        }
        String reason = "VISITOR_LEFT".equals(endReason) ? "안내 전 이탈" : "발화 없이 시간 초과";
        return new EndClassificationResult(
                hasPackage ? "UNATTENDED_DELIVERY" : "VISITOR_TIMEOUT",
                hasPackage ? "물품만 있음" : "기타·판단 불가",
                "무응답", "무응답", reason
        );
    }

    // 11주차 구현 제안. 일반 무발화와 단말 중단을 앱의 원인·확인 필요로 구분한다.
    public EndClassificationResult interrupted(boolean hasPackage, String reason) {
        return new EndClassificationResult(
                hasPackage ? "UNATTENDED_DELIVERY" : "VISITOR_TIMEOUT",
                hasPackage ? "물품만 있음" : "기타·판단 불가",
                "장애 안내", "단말 확인 필요", reason
        );
    }
}
