package com.datacat.server.push;

public record PushTokenRequest(
        String deviceToken,
        String platform
) {
}