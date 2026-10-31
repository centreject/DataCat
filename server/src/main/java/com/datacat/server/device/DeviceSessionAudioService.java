package com.datacat.server.device;

import com.datacat.server.classification.AudioClassificationResult;
import com.datacat.server.classification.AudioClassificationService;
import com.datacat.server.event.Event;
import com.datacat.server.event.EventRepository;
import com.datacat.server.event.EventStatus;
import com.datacat.server.model.AudioProcessResponse;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

import java.nio.charset.StandardCharsets;
import java.time.Instant;

@Service
public class DeviceSessionAudioService {

    // 추가 음성의 유예 기준은 구현 제안이다. 기존 사진 병합 기준과 맞춘 시작값이다.
    private static final long REANALYSIS_WINDOW_SECONDS = 30;

    private final EventRepository eventRepository;
    private final AudioClassificationService audioClassificationService;
    private final PackageReceptionService packageReceptionService;

    public DeviceSessionAudioService(
            EventRepository eventRepository,
            AudioClassificationService audioClassificationService,
            PackageReceptionService packageReceptionService
    ) {
        this.eventRepository = eventRepository;
        this.audioClassificationService = audioClassificationService;
        this.packageReceptionService = packageReceptionService;
    }

    @Transactional(readOnly = true)
    public Preparation prepare(Long eventId, String audioHash, Instant receivedAt) {
        Event event = findAcceptableEvent(eventId, audioHash, receivedAt);
        return new Preparation(event, alreadyProcessed(event, audioHash));
    }

    // 모델 호출이 끝난 뒤에만 이 저장 트랜잭션을 시작한다.
    @Transactional
    public AudioSaveResult saveAnalysis(
            Long eventId,
            String audioHash,
            AudioProcessResponse response,
            Instant receivedAt
    ) {
        Event event = findAcceptableEvent(eventId, audioHash, receivedAt);

        if (alreadyProcessed(event, audioHash)) {
            return new AudioSaveResult(event, false);
        }

        // MySQL TEXT는 최대 65,535바이트다. DB 오류 전에 잘못된 모델 결과를 거절한다.
        if (response == null || response.transcript() == null
                || response.transcript().getBytes(StandardCharsets.UTF_8).length > 65_535) {
            throw new ResponseStatusException(HttpStatus.SERVICE_UNAVAILABLE,
                    "음성 분석 결과의 전사문을 저장할 수 없습니다.");
        }

        AudioClassificationResult classification = audioClassificationService.classify(
                response,
                event.getImageProcessingStatus(),
                event.getImageNeedsReview()
        );

        event.recordAudioAnalysis(
                response.transcript(), response.purpose(), response.subtype(),
                response.summary(), audioHash
        );
        event.applyClassification(
                classification.eventType(), classification.mainCategory(),
                classification.subCategory(), classification.responsePolicy(),
                classification.processingStatus(), classification.reason(),
                classification.needsReview()
        );
        event.complete(Instant.now());

        Event saved = eventRepository.saveAndFlush(event);
        packageReceptionService.rememberCompletedEvent(saved, Instant.now());
        return new AudioSaveResult(saved, true);
    }

    // 판정표 A0: 이미지와 음성 분석이 모두 실패한 방문은 B2와 같은 분류로 종료한다.
    // HTTP 오류 응답을 성공 응답으로 바꾸지는 않는다.
    @Transactional
    public AudioFailureResult completeIfImageAnalysisFailed(Long eventId, Instant failedAt) {
        if (eventId == null || eventId < 1 || failedAt == null) {
            throw new IllegalArgumentException("방문 번호와 실패 확인 시각이 필요합니다.");
        }
        Event event = eventRepository.findById(eventId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND,
                        "해당 이벤트를 찾을 수 없습니다."));

        // 정상 사진의 일시적인 음성 실패와 이미 성공한 음성 결과는 그대로 둔다.
        if (event.getStatus() != EventStatus.WAITING_AUDIO
                || !"A0".equals(event.getImageRuleId())) {
            return new AudioFailureResult(event, false);
        }

        // 장애 안내·원인 문구의 조합은 구현 제안이다. 상세 계약은 구현 문서를 따른다.
        event.applyClassification(
                "VISITOR_TIMEOUT", "기타·판단 불가", null,
                "장애 안내", "이미지 판단 실패", "이미지·음성 분석 실패", true
        );
        event.complete(failedAt);
        Event saved = eventRepository.saveAndFlush(event);
        packageReceptionService.rememberCompletedEvent(saved, failedAt);
        return new AudioFailureResult(saved, true);
    }

    private Event findAcceptableEvent(Long eventId, String audioHash, Instant receivedAt) {
        if (eventId == null || eventId < 1) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST,
                    "eventId는 1 이상이어야 합니다.");
        }
        if (audioHash == null || !audioHash.matches("[0-9a-f]{64}") || receivedAt == null) {
            throw new IllegalArgumentException("녹음 해시와 수신 시각이 필요합니다.");
        }

        Event event = eventRepository.findById(eventId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND,
                        "해당 이벤트를 찾을 수 없습니다."));

        if (event.getStatus() == EventStatus.WAITING_AUDIO || alreadyProcessed(event, audioHash)) {
            return event;
        }

        // 음성으로 완료된 방문만 유예 시간 안에서 다른 녹음으로 다시 분석할 수 있다.
        // /end나 사진 판정으로 완료된 방문은 음성으로 다시 열지 않는다.
        if (event.getStatus() == EventStatus.COMPLETED && event.getAudioHash() != null
                && event.getLastImageReceivedAt() != null
                && !event.getLastImageReceivedAt().isBefore(
                        receivedAt.minusSeconds(REANALYSIS_WINDOW_SECONDS))) {
            return event;
        }

        throw new ResponseStatusException(HttpStatus.CONFLICT,
                "현재 이벤트는 음성을 접수할 수 없습니다. 새 방문으로 접수해 주세요.");
    }

    private boolean alreadyProcessed(Event event, String audioHash) {
        return event.getStatus() == EventStatus.COMPLETED
                && audioHash.equals(event.getAudioHash());
    }

    public record Preparation(Event event, boolean alreadyProcessed) {
    }

    public record AudioSaveResult(Event event, boolean changed) {
    }

    public record AudioFailureResult(Event event, boolean changed) {
    }
}
