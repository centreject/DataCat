package com.datacat.server.push;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

import java.time.Instant;

@Entity
@Table(name = "push_token")
public class PushToken {

    @Id
    @Column(name = "token_id", nullable = false, length = 64)
    private String tokenId;

    @Column(name = "device_token", nullable = false, length = 512)
    private String deviceToken;

    @Column(nullable = false, length = 16)
    private String platform;

    @Column(nullable = false)
    private Instant createdAt;

    @Column(nullable = false)
    private Instant updatedAt;

    protected PushToken() {
        // JPA가 DB에서 읽은 데이터로 객체를 만들 때 사용한다.
    }

    public PushToken(
            String tokenId,
            String deviceToken,
            String platform,
            Instant registeredAt
    ) {
        this.tokenId = tokenId;
        this.deviceToken = deviceToken;
        this.platform = platform;
        this.createdAt = registeredAt;
        this.updatedAt = registeredAt;
    }

    public String getTokenId() {
        return tokenId;
    }

    public String getDeviceToken() {
        return deviceToken;
    }

    public String getPlatform() {
        return platform;
    }

    public Instant getCreatedAt() {
        return createdAt;
    }

    public Instant getUpdatedAt() {
        return updatedAt;
    }

    public void registerAgain(Instant registeredAt) {
        if (registeredAt.isAfter(this.updatedAt)) {
            this.updatedAt = registeredAt;
        }
    }
}