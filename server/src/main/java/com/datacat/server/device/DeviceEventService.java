package com.datacat.server.device;

import com.datacat.server.classification.ImageClassificationResult;
import com.datacat.server.classification.ImageClassificationService;
import com.datacat.server.event.Event;
import com.datacat.server.event.EventRepository;
import com.datacat.server.event.EventStatus;
import com.datacat.server.model.VisionModelClient;
import com.datacat.server.model.VisionResponse;
import com.datacat.server.storage.SnapshotStorageService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.server.ResponseStatusException;
import tools.jackson.databind.ObjectMapper;
import com.datacat.server.push.VisitPushService;

import java.time.Instant;
import java.util.Optional;

@Service
public class DeviceEventService {

    private static final Logger log =
            LoggerFactory.getLogger(DeviceEventService.class);

    private final EventRepository eventRepository;
    private final SnapshotStorageService snapshotStorageService;
    private final VisionModelClient visionModelClient;
    private final ImageClassificationService imageClassificationService;
    private final ObjectMapper objectMapper;
    private final VisitPushService visitPushService;

    public DeviceEventService(
            EventRepository eventRepository,
            SnapshotStorageService snapshotStorageService,
            VisionModelClient visionModelClient,
            ImageClassificationService imageClassificationService,
            ObjectMapper objectMapper,
            VisitPushService visitPushService
    ) {
        this.eventRepository = eventRepository;
        this.snapshotStorageService = snapshotStorageService;
        this.visionModelClient = visionModelClient;
        this.imageClassificationService = imageClassificationService;
        this.objectMapper = objectMapper;
        this.visitPushService = visitPushService;
    }

    public synchronized CreationResult createEvent(
            DeviceEventMetadata metadata,
            MultipartFile image
    ) {
        validateMetadata(metadata);

        Instant receivedAt = Instant.now();
        Instant cutoff = receivedAt.minusSeconds(30);

        Optional<Event> recentEvent = eventRepository
                .findFirstByDeviceIdAndLastImageReceivedAtGreaterThanEqualOrderByLastImageReceivedAtDescEventIdDesc(
                        metadata.deviceId(),
                        cutoff
                );

        boolean created = recentEvent.isEmpty();

        Event event = recentEvent.orElseGet(() -> new Event(
                metadata.deviceId(),
                metadata.triggerType(),
                EventStatus.WAITING_AUDIO,
                metadata.capturedAt().toInstant()
        ));

        String previousFilename = event.getSnapshotPath();
        String filename = snapshotStorageService.save(image);

        Event saved;
        boolean notificationRequired;

        try {
            ImageAnalysis analysis = analyzeImage(
                    metadata.triggerType(),
                    image
            );

            ImageClassificationResult classification =
                    analysis.classification();

            String visionJson = analysis.vision() == null
                    ? null
                    : objectMapper.writeValueAsString(analysis.vision());

            // 사진 수신 정보만 갱신하고, 기존 판정은 아직 변경하지 않는다.
            event.recordImageReception(
                    receivedAt,
                    classification.packageCount()
            );

            event.attachSnapshot(filename);

            event.recordImageAnalysis(
                    metadata.distanceMm(),
                    visionJson
            );

            boolean classificationChanged = shouldApplyClassification(
                    event.getImageRuleId(),
                    classification.ruleId()
            );

            if (classificationChanged) {
                event.applyImageClassification(
                        classification,
                        Instant.now()
                );
            }

            // 지금은 발송하지 않고, 이후 푸시 연결에 사용할 판단값이다.
            notificationRequired = classificationChanged
                    && !"A5".equals(classification.ruleId());

            saved = eventRepository.saveAndFlush(event);

        } catch (RuntimeException exception) {
            cleanupNewSnapshot(filename, exception);
            throw exception;
        }

        cleanupPreviousSnapshot(previousFilename, filename);

        // 방문 저장에 성공했고 알림이 필요한 경우에만 푸시 작업을 요청한다.
        if (notificationRequired) {
            visitPushService.notifyVisit(saved);
        }

        DeviceEventResponse response = createDeviceResponse(saved);
        return new CreationResult(
                response,
                created,
                notificationRequired
        );
    }

    private ImageAnalysis analyzeImage(
            String triggerType,
            MultipartFile image
    ) {
        VisionResponse vision;

        try {
            vision = visionModelClient.detect(image);

        } catch (ResponseStatusException exception) {
            // 모델 연결·응답 오류만 A0로 처리한다.
            // 파일 읽기 오류 등 다른 서버 오류는 그대로 전달한다.
            if (exception.getStatusCode().value() != 503) {
                throw exception;
            }

            log.warn(
                    "Vision 분석에 실패하여 A0 판정을 사용합니다: {}",
                    exception.getReason()
            );

            return new ImageAnalysis(
                    null,
                    imageClassificationService.modelUnavailable()
            );
        }

        return new ImageAnalysis(
                vision,
                imageClassificationService.classify(
                        triggerType,
                        vision
                )
        );
    }

    private boolean shouldApplyClassification(
            String previousRuleId,
            String newRuleId
    ) {
        // 신규 이벤트 또는 이전 판정값이 없는 기존 이벤트다.
        if (previousRuleId == null) {
            return true;
        }

        // 모델 장애로 기존 판정을 덮어쓰지 않는다.
        if ("A0".equals(newRuleId)) {
            return false;
        }

        // 판정표에서 더 위에 있는 조건일 때만 변경한다.
        return priority(newRuleId) < priority(previousRuleId);
    }

    private int priority(String ruleId) {
        return switch (ruleId) {
            case "A0" -> 0;
            case "A1" -> 1;
            case "A2" -> 2;
            case "A3" -> 3;
            case "A4" -> 4;
            case "A5" -> 5;
            default -> throw new IllegalStateException(
                    "알 수 없는 사진 판정 규칙입니다: " + ruleId
            );
        };
    }

    private DeviceEventResponse createDeviceResponse(Event event) {
        if (event.getStatus() == EventStatus.WAITING_AUDIO) {
            return new DeviceEventResponse(
                    event.getEventId(),
                    event.getStatus(),
                    DeviceAction.START_RECEPTION,
                    new DeviceEventResponse.Preset(
                            1L,
                            "마이크에 말씀해 주세요."
                    )
            );
        }

        return new DeviceEventResponse(
                event.getEventId(),
                event.getStatus(),
                DeviceAction.SILENT_STANDBY,
                null
        );
    }

    private void cleanupNewSnapshot(
            String filename,
            RuntimeException originalException
    ) {
        try {
            snapshotStorageService.delete(filename);

        } catch (RuntimeException cleanupException) {
            log.error(
                    "이벤트 처리 실패 후 새 사진 정리에 실패했습니다.",
                    cleanupException
            );

            originalException.addSuppressed(cleanupException);
        }
    }

    private void cleanupPreviousSnapshot(
            String previousFilename,
            String filename
    ) {
        if (previousFilename == null
                || previousFilename.equals(filename)) {
            return;
        }

        try {
            snapshotStorageService.delete(previousFilename);

        } catch (RuntimeException cleanupException) {
            log.error(
                    "이벤트 저장은 성공했지만 이전 사진 정리에 실패했습니다.",
                    cleanupException
            );
        }
    }

    private void validateMetadata(DeviceEventMetadata metadata) {
        if (metadata == null) {
            throw badRequest("metadata가 필요합니다.");
        }

        if (metadata.deviceId() == null
                || metadata.deviceId().isBlank()
                || metadata.deviceId().length() > 100) {
            throw badRequest(
                    "deviceId는 비어 있지 않은 100자 이하 문자열이어야 합니다."
            );
        }

        if (!"TOF".equals(metadata.triggerType())
                && !"BUTTON".equals(metadata.triggerType())) {
            throw badRequest(
                    "triggerType은 TOF 또는 BUTTON이어야 합니다."
            );
        }

        if (metadata.capturedAt() == null) {
            throw badRequest("capturedAt이 필요합니다.");
        }

        if (metadata.distanceMm() != null
                && metadata.distanceMm() < 0) {
            throw badRequest("distanceMm은 0 이상이어야 합니다.");
        }
    }

    private ResponseStatusException badRequest(String message) {
        return new ResponseStatusException(
                HttpStatus.BAD_REQUEST,
                message
        );
    }

    private record ImageAnalysis(
            VisionResponse vision,
            ImageClassificationResult classification
    ) {
    }

    public record CreationResult(
            DeviceEventResponse response,
            boolean created,
            boolean notificationRequired
    ) {
    }
}