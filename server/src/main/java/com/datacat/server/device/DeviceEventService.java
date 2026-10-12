package com.datacat.server.device;

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

import java.time.Instant;
import java.util.Optional;

@Service
public class DeviceEventService {

    private static final Logger log =
            LoggerFactory.getLogger(DeviceEventService.class);

    private final EventRepository eventRepository;
    private final SnapshotStorageService snapshotStorageService;
    private final VisionModelClient visionModelClient;
    private final ObjectMapper objectMapper;

    public DeviceEventService(
            EventRepository eventRepository,
            SnapshotStorageService snapshotStorageService,
            VisionModelClient visionModelClient,
            ObjectMapper objectMapper
    ) {
        this.eventRepository = eventRepository;
        this.snapshotStorageService = snapshotStorageService;
        this.visionModelClient = visionModelClient;
        this.objectMapper = objectMapper;
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
        boolean personDetected;

        try {
            VisionResponse vision = visionModelClient.detect(image);

            personDetected = vision.detections().stream()
                    .anyMatch(detection ->
                            "person".equals(detection.label())
                    );

            event.beginImageReception(receivedAt);
            event.attachSnapshot(filename);

            event.recordImageAnalysis(
                    metadata.distanceMm(),
                    objectMapper.writeValueAsString(vision)
            );

            if (!personDetected) {
                event.complete(Instant.now());
            }

            saved = eventRepository.saveAndFlush(event);

        } catch (RuntimeException exception) {
            try {
                snapshotStorageService.delete(filename);
            } catch (RuntimeException cleanupException) {
                log.error(
                        "이벤트 저장 실패 후 새 사진 정리에 실패했습니다.",
                        cleanupException
                );

                exception.addSuppressed(cleanupException);
            }

            throw exception;
        }

        if (previousFilename != null
                && !previousFilename.equals(filename)) {
            try {
                snapshotStorageService.delete(previousFilename);
            } catch (RuntimeException cleanupException) {
                log.error(
                        "이벤트 저장은 성공했지만 이전 사진 정리에 실패했습니다.",
                        cleanupException
                );
            }
        }

        DeviceEventResponse response;

        if (personDetected) {
            response = new DeviceEventResponse(
                    saved.getEventId(),
                    saved.getStatus(),
                    DeviceAction.START_RECEPTION,
                    new DeviceEventResponse.Preset(
                            1L,
                            "마이크에 말씀해 주세요."
                    )
            );
        } else {
            response = new DeviceEventResponse(
                    saved.getEventId(),
                    saved.getStatus(),
                    DeviceAction.SILENT_STANDBY,
                    null
            );
        }

        return new CreationResult(response, created);
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

    public record CreationResult(
            DeviceEventResponse response,
            boolean created
    ) {
    }
}