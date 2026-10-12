package com.datacat.server.device;

import com.datacat.server.event.EventStatus;
import com.fasterxml.jackson.annotation.JsonInclude;

public record DeviceEventResponse(
        Long eventId,
        EventStatus status,
        DeviceAction action,

        @JsonInclude(JsonInclude.Include.NON_NULL)
        Preset preset
) {

    public record Preset(
            Long presetId,
            String text
    ) {
    }
}