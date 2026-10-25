package com.datacat.server.classification;

public record EndClassificationResult(
        String eventType,
        String mainCategory,
        String responsePolicy,
        String processingStatus,
        String reason
) {
}