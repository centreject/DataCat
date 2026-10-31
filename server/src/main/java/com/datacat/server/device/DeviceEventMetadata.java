package com.datacat.server.device;

import java.time.OffsetDateTime;

public record DeviceEventMetadata(
        String deviceId,
        String triggerType,
        Integer distanceMm,
        OffsetDateTime capturedAt
) {
}