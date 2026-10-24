package com.datacat.server.device;

import com.datacat.server.classification.ImageClassificationResult;
import com.datacat.server.event.Event;
import com.datacat.server.event.EventRepository;
import com.datacat.server.event.EventStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;

@Service
@Transactional
public class PackageReceptionService {

    private final EventRepository eventRepository;
    private final DevicePackageStateRepository packageStateRepository;

    public PackageReceptionService(
            EventRepository eventRepository,
            DevicePackageStateRepository packageStateRepository
    ) {
        this.eventRepository = eventRepository;
        this.packageStateRepository = packageStateRepository;
    }

    public ReceptionResult receive(
            DeviceEventMetadata metadata,
            ImageClassificationResult classification,
            String snapshotFilename,
            String visionJson,
            Instant receivedAt
    ) {
        validateInput(
                metadata,
                classification,
                snapshotFilename,
                receivedAt
        );

        int detectedCount = classification.packageCount();

        DevicePackageState state = packageStateRepository
                .findById(metadata.deviceId())
                .orElse(null);

        // 같은 개수 또는 더 적게 보이면 기존 물품 상태를 유지한다.
        if (state != null
                && detectedCount <= state.getPackageCount()) {

            Event existingEvent = eventRepository
                    .findById(state.getPackageEventId())
                    .orElseThrow(() -> new IllegalStateException(
                            "물품 상태에 연결된 이벤트를 찾을 수 없습니다."
                    ));

            if (!metadata.deviceId().equals(existingEvent.getDeviceId())) {
                throw new IllegalStateException(
                        "물품 상태와 이벤트의 장치 ID가 일치하지 않습니다."
                );
            }

            state.markSeen(receivedAt);
            packageStateRepository.save(state);

            return new ReceptionResult(existingEvent, false);
        }

        // 처음 감지했거나 물품 개수가 늘어난 경우 새 이벤트를 만든다.
        Event event = new Event(
                metadata.deviceId(),
                metadata.triggerType(),
                EventStatus.COMPLETED,
                metadata.capturedAt().toInstant()
        );

        event.recordImageReception(
                receivedAt,
                detectedCount
        );

        event.attachSnapshot(snapshotFilename);

        event.recordImageAnalysis(
                metadata.distanceMm(),
                visionJson
        );

        event.applyImageClassification(
                classification,
                Instant.now()
        );

        if (state != null) {
            String reason = "물품 추가 ("
                    + state.getPackageCount()
                    + "개 → "
                    + detectedCount
                    + "개)";

            event.applyClassification(
                    classification.eventType(),
                    classification.mainCategory(),
                    classification.subCategory(),
                    classification.responsePolicy(),
                    classification.processingStatus(),
                    reason,
                    classification.needsReview()
            );
        }

        Event saved = eventRepository.saveAndFlush(event);

        if (state == null) {
            state = new DevicePackageState(
                    metadata.deviceId(),
                    detectedCount,
                    saved.getEventId(),
                    receivedAt
            );
        } else {
            state.recordAdditionalPackages(
                    detectedCount,
                    saved.getEventId(),
                    receivedAt
            );
        }

        packageStateRepository.save(state);

        return new ReceptionResult(saved, true);
    }

    public void clearForDevice(String deviceId) {
        packageStateRepository.deleteById(deviceId);
    }

    private void validateInput(
            DeviceEventMetadata metadata,
            ImageClassificationResult classification,
            String snapshotFilename,
            Instant receivedAt
    ) {
        if (metadata == null
                || metadata.deviceId() == null
                || metadata.deviceId().isBlank()
                || metadata.capturedAt() == null) {
            throw new IllegalArgumentException(
                    "장치 ID와 촬영 시각이 필요합니다."
            );
        }

        if (classification == null
                || !"A3".equals(classification.ruleId())
                || classification.packageCount() == null
                || classification.packageCount() < 1) {
            throw new IllegalArgumentException(
                    "물품 수가 1 이상인 A3 판정 결과가 필요합니다."
            );
        }

        if (snapshotFilename == null
                || snapshotFilename.isBlank()
                || receivedAt == null) {
            throw new IllegalArgumentException(
                    "사진 파일 이름과 수신 시각이 필요합니다."
            );
        }
    }

    public record ReceptionResult(
            Event event,
            boolean created
    ) {
    }
}