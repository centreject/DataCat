package com.datacat.server.event;

import java.time.OffsetDateTime;
import java.time.ZoneOffset;

public record EventDetailResponse(
        Long eventId,
        String deviceId,
        String triggerType,
        String eventType,
        String purpose,
        String transcript,
        String summary,
        EventStatus status,
        String snapshotUrl,
        OffsetDateTime occurredAt,
        OffsetDateTime endedAt,
        String mainCategory,
        String subCategory,
        String responsePolicy,
        String processingStatus,
        String reason,
        boolean needsReview
) {

    public static EventDetailResponse from(Event event) {
        String snapshotUrl = null;

        if (event.getSnapshotPath() != null) {
            snapshotUrl = "/api/v1/events/"
                    + event.getEventId()
                    + "/snapshot";
        }

        OffsetDateTime endedAt = null;

        if (event.getEndedAt() != null) {
            endedAt = event.getEndedAt()
                    .atOffset(ZoneOffset.ofHours(9));
        }

        return new EventDetailResponse(
                event.getEventId(),
                event.getDeviceId(),
                event.getTriggerType(),
                event.getEventType(),
                event.getPurpose(),
                event.getTranscript(),
                event.getSummary(),
                event.getStatus(),
                snapshotUrl,
                event.getOccurredAt().atOffset(ZoneOffset.ofHours(9)),
                endedAt,
                event.getMainCategory(),
                event.getSubCategory(),
                event.getResponsePolicy(),
                event.getProcessingStatus(),
                event.getReason(),
                event.getNeedsReview()
        );
    }
}