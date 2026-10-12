package com.datacat.server.event;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

import java.time.Instant;

@Entity
@Table(name = "events")
public class Event {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long eventId;

    @Column(nullable = false, length = 100)
    private String deviceId;

    @Column(nullable = false, length = 30)
    private String triggerType;

    private Integer distanceMm;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 30)
    private EventStatus status;

    @Column(columnDefinition = "TEXT")
    private String visionResult;

    @Column(length = 100)
    private String eventType;

    @Column(length = 100)
    private String purpose;

    @Column(columnDefinition = "TEXT")
    private String transcript;

    @Column(columnDefinition = "TEXT")
    private String summary;

    @Column(length = 512)
    private String snapshotPath;

    @Column(nullable = false)
    private Instant occurredAt;

    private Instant endedAt;

    private Instant lastImageReceivedAt;

    protected Event() {
        // JPA가 DB에서 읽은 데이터로 객체를 만들 때 사용
    }

    public Event(
            String deviceId,
            String triggerType,
            EventStatus status,
            Instant occurredAt
    ) {
        this.deviceId = deviceId;
        this.triggerType = triggerType;
        this.status = status;
        this.occurredAt = occurredAt;
    }

    public Long getEventId() {
        return eventId;
    }

    public String getDeviceId() {
        return deviceId;
    }

    public String getTriggerType() {
        return triggerType;
    }

    public Integer getDistanceMm() {
        return distanceMm;
    }

    public EventStatus getStatus() {
        return status;
    }

    public String getVisionResult() {
        return visionResult;
    }

    public String getEventType() {
        return eventType;
    }

    public String getPurpose() {
        return purpose;
    }

    public String getTranscript() {
        return transcript;
    }

    public String getSummary() {
        return summary;
    }

    public String getSnapshotPath() {
        return snapshotPath;
    }

    public Instant getOccurredAt() {
        return occurredAt;
    }

    public Instant getEndedAt() {
        return endedAt;
    }
    public Instant getLastImageReceivedAt() {
        return lastImageReceivedAt;
    }

    public void attachSnapshot(String snapshotPath) {
        if (snapshotPath == null || snapshotPath.isBlank()) {
            throw new IllegalArgumentException(
                    "사진 파일 이름은 비어 있을 수 없습니다."
            );
        }

        this.snapshotPath = snapshotPath;
    }

    public void recordImageAnalysis(
            Integer distanceMm,
            String visionResult
    ) {
        this.distanceMm = distanceMm;
        this.visionResult = visionResult;
    }

    public void complete(Instant endedAt) {
        this.status = EventStatus.COMPLETED;
        this.endedAt = endedAt;
    }
    public void beginImageReception(Instant receivedAt) {
        if (receivedAt == null) {
            throw new IllegalArgumentException(
                    "사진 수신 시각은 비어 있을 수 없습니다."
            );
        }

        this.lastImageReceivedAt = receivedAt;
        this.status = EventStatus.WAITING_AUDIO;
        this.endedAt = null;
    }
}