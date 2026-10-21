package com.datacat.server.event;

import com.datacat.server.classification.ImageClassificationResult;
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

    // 적용된 사진 판정표의 행: A0, A1, A2, A3, A4, A5
    @Column(length = 10)
    private String imageRuleId;

    // 이 이벤트의 사진에서 관측한 최대 물품 수
    private Integer maxPackageCount;

    // 앱에 표시할 분류 정보
    @Column(length = 100)
    private String mainCategory;

    @Column(length = 100)
    private String subCategory;

    @Column(length = 50)
    private String responsePolicy;

    @Column(length = 50)
    private String processingStatus;

    @Column(length = 500)
    private String reason;

    // 기존 방문 기록에는 값이 없을 수 있으므로 null을 허용한다.
    private Boolean needsReview;

    protected Event() {
        // JPA가 DB에서 읽은 데이터로 객체를 만들 때 사용한다.
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

    public String getImageRuleId() {
        return imageRuleId;
    }

    public int getMaxPackageCount() {
        return maxPackageCount == null ? 0 : maxPackageCount;
    }

    public String getMainCategory() {
        return mainCategory;
    }

    public String getSubCategory() {
        return subCategory;
    }

    public String getResponsePolicy() {
        return responsePolicy;
    }

    public String getProcessingStatus() {
        return processingStatus;
    }

    public String getReason() {
        return reason;
    }

    public boolean getNeedsReview() {
        return Boolean.TRUE.equals(needsReview);
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

    public void applyClassification(
            String eventType,
            String mainCategory,
            String subCategory,
            String responsePolicy,
            String processingStatus,
            String reason,
            boolean needsReview
    ) {
        this.eventType = eventType;
        this.mainCategory = mainCategory;
        this.subCategory = subCategory;
        this.responsePolicy = responsePolicy;
        this.processingStatus = processingStatus;
        this.reason = reason;
        this.needsReview = needsReview;
    }

    public void complete(Instant endedAt) {
        this.status = EventStatus.COMPLETED;
        this.endedAt = endedAt;
    }

    // 현재 DeviceEventService가 호출하므로 기존 동작을 유지한다.
    public void beginImageReception(Instant receivedAt) {
        recordImageReception(receivedAt, null);

        this.status = EventStatus.WAITING_AUDIO;
        this.endedAt = null;
    }

    // 사진 수신 시각과 최대 물품 수만 기록한다.
    // 진행 상태와 기존 분류는 변경하지 않는다.
    public void recordImageReception(
            Instant receivedAt,
            Integer packageCount
    ) {
        if (receivedAt == null) {
            throw new IllegalArgumentException(
                    "사진 수신 시각은 비어 있을 수 없습니다."
            );
        }

        if (packageCount != null && packageCount < 0) {
            throw new IllegalArgumentException(
                    "감지된 물품 수는 0 이상이어야 합니다."
            );
        }

        this.lastImageReceivedAt = receivedAt;

        // null은 모델 장애 등으로 물품 수를 모르는 경우다.
        if (packageCount != null) {
            this.maxPackageCount = Math.max(
                    getMaxPackageCount(),
                    packageCount
            );
        }
    }

    // 접수 서비스에서 적용하기로 결정한 판정 결과를 기록한다.
    public void applyImageClassification(
            ImageClassificationResult result,
            Instant classifiedAt
    ) {
        if (result == null || classifiedAt == null) {
            throw new IllegalArgumentException(
                    "사진 판정 결과와 판정 시각이 필요합니다."
            );
        }

        if (result.status() != EventStatus.WAITING_AUDIO
                && result.status() != EventStatus.COMPLETED) {
            throw new IllegalArgumentException(
                    "사진 판정 상태는 WAITING_AUDIO 또는 COMPLETED여야 합니다."
            );
        }

        this.imageRuleId = result.ruleId();

        applyClassification(
                result.eventType(),
                result.mainCategory(),
                result.subCategory(),
                result.responsePolicy(),
                result.processingStatus(),
                result.reason(),
                result.needsReview()
        );

        this.status = result.status();

        this.endedAt = result.status() == EventStatus.COMPLETED
                ? classifiedAt
                : null;
    }
}