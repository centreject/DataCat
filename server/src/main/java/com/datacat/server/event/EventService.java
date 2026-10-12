package com.datacat.server.event;

import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Sort;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

@Service
@Transactional(readOnly = true)
public class EventService {

    private final EventRepository eventRepository;

    public EventService(EventRepository eventRepository) {
        this.eventRepository = eventRepository;
    }

    public EventPageResponse getEvents(int page, int size) {
        if (page < 0) {
            throw new ResponseStatusException(
                    HttpStatus.BAD_REQUEST,
                    "page는 0 이상이어야 합니다."
            );
        }

        if (size < 1 || size > 100) {
            throw new ResponseStatusException(
                    HttpStatus.BAD_REQUEST,
                    "size는 1 이상 100 이하여야 합니다."
            );
        }

        Sort sort = Sort.by(
                Sort.Order.desc("occurredAt"),
                Sort.Order.desc("eventId")
        );

        PageRequest pageRequest = PageRequest.of(page, size, sort);

        Page<Event> events = eventRepository.findAll(pageRequest);

        return new EventPageResponse(
                events.getContent().stream()
                        .map(EventListItemResponse::from)
                        .toList(),
                events.getNumber(),
                events.getSize(),
                events.getTotalElements()
        );
    }

    public EventDetailResponse getEvent(Long eventId) {
        if (eventId < 1) {
            throw new ResponseStatusException(
                    HttpStatus.BAD_REQUEST,
                    "eventId는 1 이상이어야 합니다."
            );
        }

        Event event = eventRepository.findById(eventId)
                .orElseThrow(() -> new ResponseStatusException(
                        HttpStatus.NOT_FOUND,
                        "해당 이벤트를 찾을 수 없습니다."
                ));

        return EventDetailResponse.from(event);
    }
}