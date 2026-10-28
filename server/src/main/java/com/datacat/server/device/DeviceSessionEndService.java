package com.datacat.server.device;

import com.datacat.server.classification.EndClassificationResult;
import com.datacat.server.classification.EndClassificationService;
import com.datacat.server.event.Event;
import com.datacat.server.event.EventRepository;
import com.datacat.server.event.EventStatus;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

import java.time.Instant;

@Service
public class DeviceSessionEndService {

    private final EventRepository eventRepository;
    private final EndClassificationService endClassificationService;
    private final PackageReceptionService packageReceptionService;

    public DeviceSessionEndService(
            EventRepository eventRepository,
            EndClassificationService endClassificationService,
            PackageReceptionService packageReceptionService
    ) {
        this.eventRepository = eventRepository;
        this.endClassificationService = endClassificationService;
        this.packageReceptionService = packageReceptionService;
    }

    // 방문 종료와 물품 상태 저장을 하나의 DB 작업으로 처리한다.
    // 중간에 저장이 실패하면 두 변경을 함께 취소한다.
    @Transactional
    public EndResult endEvent(Long eventId, DeviceEndRequest request) {
        validateRequest(eventId, request);

        Event event = eventRepository.findById(eventId)
                .orElseThrow(() -> new ResponseStatusException(
                        HttpStatus.NOT_FOUND,
                        "해당 이벤트를 찾을 수 없습니다."
                ));

        Instant endedAt = request.endedAt().toInstant();

        if (endedAt.isBefore(event.getOccurredAt())) {
            throw badRequest("endedAt은 방문 발생 시각보다 빠를 수 없습니다.");
        }

        // 재전송 또는 늦게 도착한 종료 요청으로 완료 결과를 덮어쓰지 않는다.
        if (event.getStatus() == EventStatus.COMPLETED) {
            return new EndResult(event, false);
        }

        if (event.getStatus() != EventStatus.WAITING_AUDIO) {
            throw new ResponseStatusException(
                    HttpStatus.CONFLICT,
                    "음성 접수 대기 중인 이벤트만 종료할 수 있습니다."
            );
        }

        EndClassificationResult classification =
                endClassificationService.classify(
                        request.reason(),
                        event.getPackageSeen()
                );

        event.applyClassification(
                classification.eventType(),
                classification.mainCategory(),
                null,
                classification.responsePolicy(),
                classification.processingStatus(),
                classification.reason(),
                event.getNeedsReview()
        );

        event.complete(endedAt);

        Event saved = eventRepository.saveAndFlush(event);

        // 물품이 있던 방문이면 잔류 물품 상태도 같은 트랜잭션에 저장한다.
        packageReceptionService.rememberCompletedEvent(saved, Instant.now());

        return new EndResult(saved, true);
    }

    private void validateRequest(Long eventId, DeviceEndRequest request) {
        if (eventId == null || eventId < 1) {
            throw badRequest("eventId는 1 이상이어야 합니다.");
        }

        if (request == null) {
            throw badRequest("종료 요청 내용이 필요합니다.");
        }

        if (!"VISITOR_LEFT".equals(request.reason())
                && !"TIMEOUT".equals(request.reason())) {
            throw badRequest("reason은 VISITOR_LEFT 또는 TIMEOUT이어야 합니다.");
        }

        if (request.endedAt() == null) {
            throw badRequest("endedAt이 필요합니다.");
        }
    }

    private ResponseStatusException badRequest(String message) {
        return new ResponseStatusException(HttpStatus.BAD_REQUEST, message);
    }

    public record EndResult(Event event, boolean changed) {
    }
}
