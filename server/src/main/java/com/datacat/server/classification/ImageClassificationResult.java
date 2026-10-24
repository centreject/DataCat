package com.datacat.server.classification;

import com.datacat.server.device.DeviceAction;
import com.datacat.server.event.EventStatus;

public record ImageClassificationResult(
        String ruleId,
        DeviceAction action,
        EventStatus status,
        String eventType,
        String mainCategory,
        String subCategory,
        String responsePolicy,
        String processingStatus,
        String reason,
        boolean needsReview,
        Integer packageCount
) {
}