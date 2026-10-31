package com.datacat.server.classification;

public record AudioClassificationResult(
        String eventType,
        String mainCategory,
        String subCategory,
        String responsePolicy,
        String processingStatus,
        String reason,
        boolean needsReview
) {
}
