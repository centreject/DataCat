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

    @org.junit.jupiter.api.Test
    void packageSeenStaysTrueAfterEmptyAndUnknownPhotos() {
        Event event = new Event("door", "TOF", EventStatus.WAITING_AUDIO, java.time.Instant.now());
        event.recordImageReception(java.time.Instant.now(), 1);
        event.recordImageReception(java.time.Instant.now(), 0);
        event.recordImageReception(java.time.Instant.now(), null);
        org.junit.jupiter.api.Assertions.assertTrue(event.getPackageSeen());
    }

    @org.junit.jupiter.api.Test
    void legacyMaximumCountSupportsExistingRows() {
        Event event = new Event("door", "TOF", EventStatus.WAITING_AUDIO, java.time.Instant.now());
        org.springframework.test.util.ReflectionTestUtils.setField(event, "maxPackageCount", 2);
        org.junit.jupiter.api.Assertions.assertTrue(event.getPackageSeen());
        event.recordImageReception(java.time.Instant.now(), 0);
        org.junit.jupiter.api.Assertions.assertTrue(event.getPackageSeen());
    }
}