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

    public PackageReceptionService(EventRepository eventRepository,
                                   DevicePackageStateRepository packageStateRepository) {
        this.eventRepository = eventRepository;
        this.packageStateRepository = packageStateRepository;
    }

    public ReceptionResult receive(DeviceEventMetadata metadata,
                                   ImageClassificationResult classification,
                                   String snapshotFilename, String visionJson, Instant receivedAt) {
        if (metadata == null || metadata.deviceId() == null || metadata.deviceId().isBlank()
                || metadata.capturedAt() == null || classification == null
                || !"A3".equals(classification.ruleId())
                || classification.packageCount() == null || classification.packageCount() < 1
                || snapshotFilename == null || snapshotFilename.isBlank() || receivedAt == null) {
            throw new IllegalArgumentException("장치·촬영 정보와 물품이 있는 A3 판정이 필요합니다.");
        }

        DevicePackageState state = packageStateRepository.findById(metadata.deviceId()).orElse(null);

        // 10-23 판정표 A3-2: 개수가 달라져도 존재 상태가 유지되면 다시 알리지 않는다.
        if (state != null && state.getPackagePresent()) {
            Event previous = eventRepository.findById(state.getPackageEventId())
                    .orElseThrow(() -> new IllegalStateException("물품 상태에 연결된 이벤트가 없습니다."));
            if (!metadata.deviceId().equals(previous.getDeviceId())) {
                throw new IllegalStateException("물품 상태와 이벤트의 장치 ID가 다릅니다.");
            }
            state.markSeen(receivedAt);
            packageStateRepository.save(state);
            return new ReceptionResult(previous, false);
        }

        Event event = new Event(metadata.deviceId(), metadata.triggerType(),
                EventStatus.COMPLETED, metadata.capturedAt().toInstant());
        event.recordImageReception(receivedAt, classification.packageCount());
        event.attachSnapshot(snapshotFilename);
        event.recordImageAnalysis(metadata.distanceMm(), visionJson);
        event.applyImageClassification(classification, Instant.now());
        Event saved = eventRepository.saveAndFlush(event);

        packageStateRepository.save(new DevicePackageState(
                metadata.deviceId(), saved.getEventId(), receivedAt));
        return new ReceptionResult(saved, true);
    }

    public void observePresentIfKnown(String deviceId, Instant receivedAt) {
        DevicePackageState state = packageStateRepository.findById(deviceId).orElse(null);
        if (state != null && state.getPackagePresent()) {
            state.markSeen(receivedAt);
            packageStateRepository.save(state);
        }
    }

    public void observeMissing(String deviceId) {
        DevicePackageState state = packageStateRepository.findById(deviceId).orElse(null);
        if (state == null || !state.getPackagePresent()) return;
        if (state.recordMissing()) {
            packageStateRepository.delete(state);
        } else {
            packageStateRepository.save(state);
        }
    }

    // 음성 또는 종료 판정과 같은 트랜잭션에서 호출한다.
    public void rememberCompletedEvent(Event event, Instant receivedAt) {
        if (event == null || event.getEventId() == null
                || event.getStatus() != EventStatus.COMPLETED || receivedAt == null) {
            throw new IllegalArgumentException("저장된 완료 이벤트와 물품 확인 시각이 필요합니다.");
        }
        if (!event.getPackageSeen()) return;

        DevicePackageState state = packageStateRepository.findById(event.getDeviceId()).orElse(null);
        if (state == null || !state.getPackagePresent()) {
            state = new DevicePackageState(event.getDeviceId(), event.getEventId(), receivedAt);
        } else {
            // 새 응대 세션을 이미 알렸으므로 이후 재알림은 이 세션에 연결한다.
            state.rememberSession(event.getEventId(), receivedAt);
        }
        packageStateRepository.save(state);
    }

    public void clearForDevice(String deviceId) {
        packageStateRepository.deleteById(deviceId);
    }

    public record ReceptionResult(Event event, boolean created) { }
}
