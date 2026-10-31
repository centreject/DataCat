package com.datacat.server.device;

import com.datacat.server.classification.ImageClassificationResult;
import com.datacat.server.classification.ImageClassificationService;
import com.datacat.server.event.Event;
import com.datacat.server.event.EventStatus;
import com.datacat.server.model.VisionModelClient;
import com.datacat.server.model.VisionResponse;
import com.datacat.server.model.AudioModelClient;
import com.datacat.server.model.AudioProcessResponse;
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
import java.io.IOException;
import java.io.InputStream;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.Arrays;
import java.util.HexFormat;

@Service
public class DeviceEventService {

    private static final Logger log =
            LoggerFactory.getLogger(DeviceEventService.class);

    private final DeviceSessionImageService deviceSessionImageService;
    private final SnapshotStorageService snapshotStorageService;
    private final VisionModelClient visionModelClient;
    private final ImageClassificationService imageClassificationService;
    private final ObjectMapper objectMapper;
    private final VisitPushService visitPushService;
    private final DeviceSessionEndService deviceSessionEndService;
    private final AudioModelClient audioModelClient;
    private final DeviceSessionAudioService deviceSessionAudioService;

    public DeviceEventService(
            DeviceSessionImageService deviceSessionImageService,
            SnapshotStorageService snapshotStorageService,
            VisionModelClient visionModelClient,
            ImageClassificationService imageClassificationService,
            ObjectMapper objectMapper,
            VisitPushService visitPushService,
            DeviceSessionEndService deviceSessionEndService,
            AudioModelClient audioModelClient,
            DeviceSessionAudioService deviceSessionAudioService
    ) {
        this.deviceSessionImageService = deviceSessionImageService;
        this.snapshotStorageService = snapshotStorageService;
        this.visionModelClient = visionModelClient;
        this.imageClassificationService = imageClassificationService;
        this.objectMapper = objectMapper;
        this.visitPushService = visitPushService;
        this.deviceSessionEndService = deviceSessionEndService;
        this.audioModelClient = audioModelClient;
        this.deviceSessionAudioService = deviceSessionAudioService;
    }

    public synchronized CreationResult createEvent(
            DeviceEventMetadata metadata,
            MultipartFile image
    ) {
        validateMetadata(metadata);
        Instant receivedAt = Instant.now();
        String filename = snapshotStorageService.save(image);
        DeviceSessionImageService.ImageSaveResult result;

        try {
            // 파일 검사·Vision HTTP 호출은 저장 트랜잭션 밖에서 실행한다.
            ImageAnalysis analysis = analyzeImage(metadata.triggerType(), image);
            String visionJson = analysis.vision() == null
                    ? null : objectMapper.writeValueAsString(analysis.vision());
            result = deviceSessionImageService.save(metadata, analysis.classification(),
                    filename, visionJson, receivedAt);
        } catch (RuntimeException exception) {
            cleanupNewSnapshot(filename, exception);
            throw exception;
        }

        // 저장이 커밋된 다음에만 이전 사진 또는 사용하지 않은 새 사진을 지운다.
        if (result.newSnapshotUsed()) {
            cleanupUnusedSnapshot(result.previousFilename(), filename);
        } else {
            cleanupUnusedSnapshot(filename, result.event().getSnapshotPath());
        }
        if (result.notificationRequired()) {
            visitPushService.notifyVisit(result.event());
        }
        return new CreationResult(createDeviceResponse(result.event()), result.created(),
                result.notificationRequired());
    }

    // createEvent와 같은 객체의 잠금을 사용해 사진 처리와 종료 처리가 겹치지 않게 한다.
    // 현재처럼 Spring 서버 한 개를 실행하는 MVP 범위의 동시성 제어다.
    public synchronized DeviceEventResponse endEvent(
            Long eventId,
            DeviceEndRequest request
    ) {
        DeviceSessionEndService.EndResult result =
                deviceSessionEndService.endEvent(eventId, request);

        // 별도 서비스의 트랜잭션이 커밋된 다음 푸시를 요청한다.
        // 이미 완료된 방문에 대한 재요청에는 다시 발송하지 않는다.
        if (result.changed()) {
            visitPushService.notifyVisit(result.event());
        }

        return new DeviceEventResponse(
                result.event().getEventId(),
                result.event().getStatus(),
                DeviceAction.END_SESSION,
                null
        );
    }

    // 사진·종료 요청과 같은 단일 서버 내 잠금을 사용한다.
    public synchronized DeviceEventResponse receiveAudio(Long eventId, MultipartFile audio) {
        if (eventId == null || eventId < 1) {
            throw badRequest("eventId는 1 이상이어야 합니다.");
        }
        if (audio == null || audio.isEmpty()) {
            throw badRequest("음성 파일이 비어 있습니다.");
        }
        if (audio.getSize() > 16L * 1024 * 1024) {
            throw badRequest("음성 파일은 16MB 이하여야 합니다.");
        }

        Instant receivedAt = Instant.now();
        String hash = audioHash(audio);
        DeviceSessionAudioService.Preparation preparation =
                deviceSessionAudioService.prepare(eventId, hash, receivedAt);

        if (preparation.alreadyProcessed()) {
            return completedAudioResponse(preparation.event());
        }

        DeviceSessionAudioService.AudioSaveResult result;
        try {
            // HTTP 모델 호출 중에는 DB 트랜잭션을 열어 두지 않는다.
            AudioProcessResponse modelResponse = audioModelClient.process(audio);
            result = deviceSessionAudioService.saveAnalysis(eventId, hash, modelResponse, receivedAt);
        } catch (ResponseStatusException exception) {
            if (exception.getStatusCode().value() == 503) {
                // 실패한 저장 트랜잭션이 종료된 뒤 별도 트랜잭션에서 A0 종료 여부를 확인한다.
                DeviceSessionAudioService.AudioFailureResult failure =
                        deviceSessionAudioService.completeIfImageAnalysisFailed(eventId, Instant.now());
                if (failure.changed()) {
                    visitPushService.notifyVisit(failure.event());
                }
            }
            throw exception;
        }

        if (result.changed()) {
            visitPushService.notifyVisit(result.event());
        }
        return completedAudioResponse(result.event());
    }

    private DeviceEventResponse completedAudioResponse(Event event) {
        return new DeviceEventResponse(
                event.getEventId(), event.getStatus(), DeviceAction.PLAY_PRESET,
                new DeviceEventResponse.Preset(2L, "접수되었습니다.")
        );
    }

    private String audioHash(MultipartFile audio) {
        byte[] buffer = new byte[8_192];
        try (InputStream input = audio.getInputStream()) {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            long total = 0;
            int size;
            while ((size = input.read(buffer)) != -1) {
                total += size;
                if (total > 16L * 1024 * 1024) {
                    throw badRequest("음성 파일은 16MB 이하여야 합니다.");
                }
                digest.update(buffer, 0, size);
            }
            return HexFormat.of().formatHex(digest.digest());
        } catch (IOException exception) {
            throw new ResponseStatusException(HttpStatus.INTERNAL_SERVER_ERROR,
                    "음성 파일을 읽을 수 없습니다.", exception);
        } catch (NoSuchAlgorithmException exception) {
            throw new IllegalStateException("SHA-256을 사용할 수 없습니다.", exception);
        } finally {
            Arrays.fill(buffer, (byte) 0);
        }
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

    private void cleanupUnusedSnapshot(
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
                    "이벤트 저장은 성공했지만 사용하지 않는 사진 정리에 실패했습니다.",
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
