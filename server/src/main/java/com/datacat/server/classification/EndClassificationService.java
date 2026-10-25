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
        if (!"VISITOR_LEFT".equals(endReason) && !"TIMEOUT".equals(endReason)) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST,
                    "reason은 VISITOR_LEFT 또는 TIMEOUT이어야 합니다.");
        }
        String reason = "VISITOR_LEFT".equals(endReason) ? "안내 전 이탈" : "발화 없이 시간 초과";
        return new EndClassificationResult(
                hasPackage ? "UNATTENDED_DELIVERY" : "VISITOR_TIMEOUT",
                hasPackage ? "물품만 있음" : "기타·판단 불가",
                "무응답", "무응답", reason
        );
    }
}
