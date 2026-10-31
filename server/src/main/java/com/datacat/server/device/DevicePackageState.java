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

    // 기존 DB의 NOT NULL 컬럼과의 호환 값이다. 새 판정에서는 개수를 비교하지 않는다.
    @Column(name = "package_count", nullable = false)
    private int legacyPackageCount = 1;

    // 기존 행에 안전하게 컬럼을 추가하기 위해 null을 허용한다.
    private Boolean packagePresent;
    private Integer missCount;

    @Column(nullable = false)
    private Long packageEventId;

    @Column(nullable = false)
    private Instant firstSeenAt;

    @Column(nullable = false)
    private Instant lastSeenAt;

    protected DevicePackageState() {
        // JPA용 생성자
    }

    public DevicePackageState(String deviceId, Long packageEventId, Instant receivedAt) {
        if (deviceId == null || deviceId.isBlank() || deviceId.length() > 100) {
            throw new IllegalArgumentException("deviceId는 비어 있지 않은 100자 이하 문자열이어야 합니다.");
        }
        validateEvent(packageEventId, receivedAt);
        this.deviceId = deviceId;
        this.packageEventId = packageEventId;
        this.packagePresent = true;
        this.missCount = 0;
        this.firstSeenAt = receivedAt;
        this.lastSeenAt = receivedAt;
    }

    public String getDeviceId() { return deviceId; }
    public boolean getPackagePresent() {
        return packagePresent == null ? legacyPackageCount > 0 : packagePresent;
    }
    public int getMissCount() { return missCount == null ? 0 : missCount; }
    public Long getPackageEventId() { return packageEventId; }
    public Instant getFirstSeenAt() { return firstSeenAt; }
    public Instant getLastSeenAt() { return lastSeenAt; }

    // 물품이 다시 보이면 마지막 확인 시각을 갱신하고 미감지 횟수를 0으로 한다.
    public void markSeen(Instant receivedAt) {
        if (receivedAt == null) {
            throw new IllegalArgumentException("물품 확인 시각이 필요합니다.");
        }
        packagePresent = true;
        missCount = 0;
        if (receivedAt.isAfter(lastSeenAt)) lastSeenAt = receivedAt;
    }

    // 사람·물품 모두 없는 A5에서만 호출한다. 2가 되면 서비스가 상태 행을 지운다.
    public boolean recordMissing() {
        missCount = Math.min(2, getMissCount() + 1);
        return missCount >= 2;
    }

    public void rememberSession(Long eventId, Instant receivedAt) {
        validateEvent(eventId, receivedAt);
        packageEventId = eventId;
        markSeen(receivedAt);
    }

    private void validateEvent(Long eventId, Instant receivedAt) {
        if (eventId == null || eventId < 1 || receivedAt == null) {
            throw new IllegalArgumentException("저장된 이벤트 ID와 물품 확인 시각이 필요합니다.");
        }
    }
}
