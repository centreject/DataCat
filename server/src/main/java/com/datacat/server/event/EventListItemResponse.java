package com.datacat.server.event;

import java.time.OffsetDateTime;
import java.time.ZoneOffset;

public record EventListItemResponse(
        Long eventId,
        String deviceId,
        String eventType,
        String purpose,
        String summary,
        EventStatus status,
        OffsetDateTime occurredAt,
        String snapshotUrl
) {

    public static EventListItemResponse from(Event event) {
        String snapshotUrl = null;

        if (event.getSnapshotPath() != null) {
            snapshotUrl = "/api/v1/events/"
                    + event.getEventId()
                    + "/snapshot";
        }

        return new EventListItemResponse(
                event.getEventId(),
                event.getDeviceId(),
                event.getEventType(),
                event.getPurpose(),
                event.getSummary(),
                event.getStatus(),
                event.getOccurredAt().atOffset(ZoneOffset.ofHours(9)),
                snapshotUrl
        );
    }
}