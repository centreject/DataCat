package com.datacat.server.event;

import java.util.List;

public record EventPageResponse(
        List<EventListItemResponse> content,
        int page,
        int size,
        long totalElements
) {
}