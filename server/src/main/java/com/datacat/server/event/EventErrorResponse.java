package com.datacat.server.event;

public record EventErrorResponse(
        String code,
        String message
) {
}