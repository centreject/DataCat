package com.datacat.server.device;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Configuration;
import org.springframework.scheduling.annotation.EnableScheduling;
import org.springframework.scheduling.annotation.Scheduled;

@Configuration(proxyBeanMethods = false)
@EnableScheduling
@ConditionalOnProperty(name = "datacat.session.expiry-enabled", havingValue = "true", matchIfMissing = true)
public class SessionExpiryScheduler {
    private final DeviceEventService service;
    private final long inactivityMs;

    public SessionExpiryScheduler(DeviceEventService service,
                                  @Value("${datacat.session.idle-timeout-ms:120000}") long inactivityMs) {
        if (inactivityMs <= 0) throw new IllegalArgumentException("세션 만료 시간은 양수여야 합니다.");
        this.service = service;
        this.inactivityMs = inactivityMs;
    }

    @Scheduled(fixedDelayString = "${datacat.session.expiry-check-ms:5000}",
               initialDelayString = "${datacat.session.expiry-check-ms:5000}")
    public void expireInactiveSessions() {
        service.expireInactiveSessions(inactivityMs);
    }
}
