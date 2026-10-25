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

    @Column(length = 100)
    private String subtype;

    @Column(columnDefinition = "TEXT")
    private String transcript;

    @Column(columnDefinition = "TEXT")
    private String summary;

    // 마지막으로 저장한 녹음의 SHA-256. 원본 음성은 저장하지 않는다.
    @Column(length = 64)
    private String audioHash;

    @Column(length = 512)
    private String snapshotPath;

    @Column(nullable = false)
    private Instant occurredAt;

    private Instant endedAt;

    private Instant lastImageReceivedAt;

    // 적용된 사진 판정표의 행: A0, A1, A2, A3, A4, A5
    @Column(length = 10)
    private String imageRuleId;

    // 음성 재분석 이후에도 사진 단계의 판정 정보를 보존한다.
    @Column(length = 50)
    private String imageProcessingStatus;

    private Boolean imageNeedsReview;

    // 이 이벤트의 사진에서 관측한 최대 물품 수
    private Integer maxPackageCount;

    // 최신 판정표는 개수 대신 세션 중 물품을 한 번이라도 봤는지만 사용한다.
    // 기존 데이터에는 값이 없으므로 이전 최대 개수로 보완해 읽는다.
    private Boolean packageSeen;

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

    public String getSubtype() {
        return subtype;
    }

    public String getAudioHash() {
        return audioHash;
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

    public String getImageProcessingStatus() {
        if (imageProcessingStatus != null) {
            return imageProcessingStatus;
        }
        // 새 컬럼이 비어 있는 기존 방문에도 적용한다.
        return "A0".equals(imageRuleId) ? "이미지 판단 실패" : processingStatus;
    }

    public boolean getImageNeedsReview() {
        if (imageNeedsReview != null) {
            return Boolean.TRUE.equals(imageNeedsReview);
        }
        return getNeedsReview() || "A0".equals(imageRuleId);
    }

    public int getMaxPackageCount() {
        return maxPackageCount == null ? 0 : maxPackageCount;
    }

    public boolean getPackageSeen() {
        return packageSeen == null ? getMaxPackageCount() > 0 : packageSeen;
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

    public void recordAudioAnalysis(
            String transcript,
            String purpose,
            String subtype,
            String summary,
            String audioHash
    ) {
        if (transcript == null || purpose == null || purpose.isBlank()
                || summary == null || audioHash == null
                || !audioHash.matches("[0-9a-f]{64}")) {
            throw new IllegalArgumentException("검증된 음성 분석 결과와 녹음 해시가 필요합니다.");
        }

        // 기존 방문은 첫 음성 결과로 덮어쓰기 전에 사진 값을 보관한다.
        if (imageProcessingStatus == null) {
            String photoStatus = getImageProcessingStatus();
            imageProcessingStatus = photoStatus == null ? "정상" : photoStatus;
        }
        if (imageNeedsReview == null) {
            imageNeedsReview = getImageNeedsReview();
        }

        this.transcript = transcript;
        this.purpose = purpose;
        this.subtype = subtype;
        this.summary = summary;
        this.audioHash = audioHash;
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
            this.packageSeen = getPackageSeen() || packageCount > 0;
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
        this.imageProcessingStatus = result.processingStatus();
        this.imageNeedsReview = result.needsReview();

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
