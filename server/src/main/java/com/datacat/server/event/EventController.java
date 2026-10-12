package com.datacat.server.event;

import org.springframework.core.io.Resource;
import org.springframework.http.CacheControl;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/events")
public class EventController {

    private final EventService eventService;

    public EventController(EventService eventService) {
        this.eventService = eventService;
    }

    @GetMapping
    public EventPageResponse getEvents(
            @RequestParam(name = "page", defaultValue = "0") int page,
            @RequestParam(name = "size", defaultValue = "20") int size
    ) {
        return eventService.getEvents(page, size);
    }

    @GetMapping("/{eventId}")
    public EventDetailResponse getEvent(
            @PathVariable("eventId") Long eventId
    ) {
        return eventService.getEvent(eventId);
    }

    @GetMapping("/{eventId}/snapshot")
    public ResponseEntity<Resource> getSnapshot(
            @PathVariable("eventId") Long eventId
    ) {
        Resource snapshot = eventService.getSnapshot(eventId);

        return ResponseEntity.ok()
                .contentType(MediaType.IMAGE_JPEG)
                .cacheControl(CacheControl.noStore())
                .body(snapshot);
    }
}