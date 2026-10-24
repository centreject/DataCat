package com.datacat.server.device;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

import java.time.Instant;

@Entity
@Table(name = "device_package_states")
public class DevicePackageState {

    @Id
    @Column(nullable = false, length = 100)
    private String deviceId;

    @Column(nullable = false)
    private int packageCount;

    @Column(nullable = false)
    private Long packageEventId;

    @Column(nullable = false)
    private Instant firstSeenAt;

    @Column(nullable = false)
    private Instant lastSeenAt;

    protected DevicePackageState() {
        // JPA가 DB에서 읽은 데이터로 객체를 만들 때 사용한다.
    }

    public DevicePackageState(
            String deviceId,
            int packageCount,
            Long packageEventId,
            Instant receivedAt
    ) {
        if (deviceId == null
                || deviceId.isBlank()
                || deviceId.length() > 100) {
            throw new IllegalArgumentException(
                    "deviceId는 비어 있지 않은 100자 이하 문자열이어야 합니다."
            );
        }

        validatePackageValues(
                packageCount,
                packageEventId,
                receivedAt
        );

        this.deviceId = deviceId;
        this.packageCount = packageCount;
        this.packageEventId = packageEventId;
        this.firstSeenAt = receivedAt;
        this.lastSeenAt = receivedAt;
    }

    public String getDeviceId() {
        return deviceId;
    }

    public int getPackageCount() {
        return packageCount;
    }

    public Long getPackageEventId() {
        return packageEventId;
    }

    public Instant getFirstSeenAt() {
        return firstSeenAt;
    }

    public Instant getLastSeenAt() {
        return lastSeenAt;
    }

    // 같은 물품이 계속 보이면 마지막 확인 시각만 갱신한다.
    public void markSeen(Instant receivedAt) {
        if (receivedAt == null) {
            throw new IllegalArgumentException(
                    "물품 확인 시각은 비어 있을 수 없습니다."
            );
        }

        if (receivedAt.isAfter(this.lastSeenAt)) {
            this.lastSeenAt = receivedAt;
        }
    }

    // 물품 개수가 늘어난 경우 새 개수와 이벤트 ID를 기록한다.
    public void recordAdditionalPackages(
            int newPackageCount,
            Long newPackageEventId,
            Instant receivedAt
    ) {
        validatePackageValues(
                newPackageCount,
                newPackageEventId,
                receivedAt
        );

        if (newPackageCount <= this.packageCount) {
            throw new IllegalArgumentException(
                    "추가 물품 기록은 기존 물품 수보다 많아야 합니다."
            );
        }

        this.packageCount = newPackageCount;
        this.packageEventId = newPackageEventId;
        markSeen(receivedAt);
    }

    private void validatePackageValues(
            int packageCount,
            Long packageEventId,
            Instant receivedAt
    ) {
        if (packageCount < 1) {
            throw new IllegalArgumentException(
                    "저장할 물품 수는 1 이상이어야 합니다."
            );
        }

        if (packageEventId == null || packageEventId < 1) {
            throw new IllegalArgumentException(
                    "저장된 이벤트 ID가 필요합니다."
            );
        }

        if (receivedAt == null) {
            throw new IllegalArgumentException(
                    "물품 확인 시각은 비어 있을 수 없습니다."
            );
        }
    }
}