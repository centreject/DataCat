package com.datacat.server.device;

import com.datacat.server.classification.ImageClassificationResult;
import com.datacat.server.event.Event;
import com.datacat.server.event.EventRepository;
import com.datacat.server.event.EventStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;

@Service
public class DeviceSessionImageService {

    private final EventRepository eventRepository;
    private final PackageReceptionService packageReceptionService;

    public DeviceSessionImageService(EventRepository eventRepository,
                                     PackageReceptionService packageReceptionService) {
        this.eventRepository = eventRepository;
        this.packageReceptionService = packageReceptionService;
    }

    // 모델 호출 후에 시작한다. 방문과 물품 상태가 함께 커밋되거나 함께 취소된다.
    @Transactional
    public ImageSaveResult save(DeviceEventMetadata metadata,
                                ImageClassificationResult classification,
                                String filename, String visionJson, Instant receivedAt) {
        Event recent = eventRepository
                .findFirstByDeviceIdAndLastImageReceivedAtGreaterThanEqualOrderByLastImageReceivedAtDescEventIdDesc(
                        metadata.deviceId(), receivedAt.minusSeconds(30))
                .filter(event -> event.getStatus() != EventStatus.FAILED)
                .orElse(null);

        // 진행 중인 음성 접수에는 물품 사진도 세션 사진으로 모은다.
        boolean activeReception = recent != null && recent.getStatus() == EventStatus.WAITING_AUDIO;
        if ("A3".equals(classification.ruleId()) && !activeReception) {
            PackageReceptionService.ReceptionResult result = packageReceptionService.receive(
                    metadata, classification, filename, visionJson, receivedAt);
            return new ImageSaveResult(result.event(), result.created(), result.created(),
                    null, result.created());
        }

        // 물품만 남은 완료 기록 뒤 새 사람·벨 접수는 새 응대 세션이다.
        // 그 외 방문은 기존 30초 사진 병합 규칙을 유지한다.
        if (isReception(classification.ruleId()) && recent != null
                && recent.getStatus() == EventStatus.COMPLETED
                && "물품만 있음".equals(recent.getMainCategory())) {
            recent = null;
        }
        boolean created = recent == null;
        Event event = created
                ? new Event(metadata.deviceId(), metadata.triggerType(),
                            EventStatus.WAITING_AUDIO, metadata.capturedAt().toInstant())
                : recent;
        String previousFilename = event.getSnapshotPath();

        event.recordImageReception(receivedAt, classification.packageCount());
        event.attachSnapshot(filename);
        event.recordImageAnalysis(metadata.distanceMm(), visionJson);

        boolean changed = shouldApplyClassification(event.getImageRuleId(), classification.ruleId());
        // 이전 버전에서 사진 판정값 없이 생성된 음성 대기 방문도 보호한다.
        if (activeReception && "A3".equals(classification.ruleId())) changed = false;
        if (changed) event.applyImageClassification(classification, Instant.now());

        Event saved = eventRepository.saveAndFlush(event);
        if ("A5".equals(classification.ruleId())) {
            packageReceptionService.observeMissing(metadata.deviceId());
        } else if (classification.packageCount() != null && classification.packageCount() > 0) {
            packageReceptionService.observePresentIfKnown(metadata.deviceId(), receivedAt);
        }

        return new ImageSaveResult(saved, created, changed && !"A5".equals(classification.ruleId()),
                previousFilename, true);
    }

    private boolean isReception(String rule) {
        return "A0".equals(rule) || "A1".equals(rule) || "A2".equals(rule);
    }

    private boolean shouldApplyClassification(String previous, String next) {
        if (previous == null) return true;
        if ("A0".equals(next)) return false;
        return priority(next) < priority(previous);
    }

    private int priority(String rule) {
        return switch (rule) {
            case "A0" -> 0;
            case "A1" -> 1;
            case "A2" -> 2;
            case "A3" -> 3;
            case "A4" -> 4;
            case "A5" -> 5;
            default -> throw new IllegalStateException("알 수 없는 사진 판정입니다: " + rule);
        };
    }

    public record ImageSaveResult(Event event, boolean created, boolean notificationRequired,
                                  String previousFilename, boolean newSnapshotUsed) { }
}
