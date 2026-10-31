package com.datacat.server.device;

import java.time.OffsetDateTime;

public record DeviceEndRequest(
        String reason,
        OffsetDateTime endedAt
) {
}