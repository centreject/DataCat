package com.datacat.server.event;

import org.junit.jupiter.api.Test;

import java.time.Instant;

import static org.junit.jupiter.api.Assertions.assertEquals;

class EventImageStateTests {

    @Test
    void receivingAnotherImageDoesNotReopenCompletedEvent() {
        Instant startedAt = Instant.parse("2026-10-21T05:00:00Z");
        Instant endedAt = startedAt.plusSeconds(1);
        Instant receivedAt = startedAt.plusSeconds(2);

        Event event = new Event(
                "test-door-01",
                "TOF",
                EventStatus.WAITING_AUDIO,
                startedAt
        );

        event.complete(endedAt);

        event.recordImageReception(receivedAt, 1);

        assertEquals(EventStatus.COMPLETED, event.getStatus());
        assertEquals(endedAt, event.getEndedAt());
        assertEquals(receivedAt, event.getLastImageReceivedAt());
    }

    @Test
    void fewerOrUnknownPackagesDoNotReduceMaximumCount() {
        Instant startedAt = Instant.parse("2026-10-21T05:00:00Z");

        Event event = new Event(
                "test-door-01",
                "TOF",
                EventStatus.WAITING_AUDIO,
                startedAt
        );

        event.recordImageReception(startedAt, 2);
        event.recordImageReception(startedAt.plusSeconds(1), 1);
        event.recordImageReception(startedAt.plusSeconds(2), 0);
        event.recordImageReception(startedAt.plusSeconds(3), null);

        assertEquals(2, event.getMaxPackageCount());
    }
}