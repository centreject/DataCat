package com.datacat.server.device;

import com.datacat.server.classification.ImageClassificationService;
import com.datacat.server.event.Event;
import com.datacat.server.event.EventRepository;
import com.datacat.server.event.EventStatus;
import com.datacat.server.model.VisionResponse;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.util.ReflectionTestUtils;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;
import java.time.ZoneOffset;
import java.util.List;
import java.util.UUID;
import java.util.stream.IntStream;

import static org.junit.jupiter.api.Assertions.*;

@SpringBootTest
@ActiveProfiles("test")
@Transactional
class PackageReceptionServiceTests {
    @Autowired private PackageReceptionService service;
    @Autowired private ImageClassificationService classifier;
    @Autowired private EventRepository events;
    @Autowired private DevicePackageStateRepository states;
    private String deviceId;
    private final Instant firstAt = Instant.parse("2026-10-24T06:00:00Z");

    @BeforeEach void setUp() { deviceId = "presence-db-" + UUID.randomUUID(); }

    @Test void samePackageAfterThirtySecondsReusesEvent() {
        long count = events.count();
        var first = receive(1, firstAt);
        var repeated = receive(1, firstAt.plusSeconds(61));
        assertTrue(first.created());
        assertFalse(repeated.created());
        assertEquals(first.event().getEventId(), repeated.event().getEventId());
        assertEquals(count + 1, events.count());
        var state = states.findById(deviceId).orElseThrow();
        assertTrue(state.getPackagePresent());
        assertEquals(firstAt, state.getFirstSeenAt());
        assertEquals(firstAt.plusSeconds(61), state.getLastSeenAt());
        assertEquals("photo.jpg", repeated.event().getSnapshotPath());
    }

    @Test void changedCountsNeverCreateAnotherArrivalWhilePresent() {
        long count = events.count();
        var first = receive(1, firstAt);
        var more = receive(3, firstAt.plusSeconds(61));
        var fewer = receive(1, firstAt.plusSeconds(122));
        assertFalse(more.created());
        assertFalse(fewer.created());
        assertEquals(first.event().getEventId(), more.event().getEventId());
        assertEquals(first.event().getEventId(), fewer.event().getEventId());
        assertEquals(count + 1, events.count());
    }

    @Test void oneMissThenPackageResetsMissCount() {
        var first = receive(1, firstAt);
        service.observeMissing(deviceId);
        assertEquals(1, states.findById(deviceId).orElseThrow().getMissCount());
        var repeated = receive(2, firstAt.plusSeconds(61));
        assertFalse(repeated.created());
        var state = states.findById(deviceId).orElseThrow();
        assertEquals(0, state.getMissCount());
        assertEquals(first.event().getEventId(), state.getPackageEventId());
    }

    @Test void twoMissesClearStateButKeepHistoryAndAllowNextArrival() {
        var first = receive(1, firstAt);
        service.observeMissing(deviceId);
        assertTrue(states.existsById(deviceId));
        service.observeMissing(deviceId);
        assertFalse(states.existsById(deviceId));
        assertTrue(events.existsById(first.event().getEventId()));
        var next = receive(1, firstAt.plusSeconds(61));
        assertTrue(next.created());
        assertNotEquals(first.event().getEventId(), next.event().getEventId());
    }

    @Test void completedSessionReplacesReferenceWithoutResettingContinuousResidencyStart() {
        receive(2, firstAt);
        service.observeMissing(deviceId);
        Event session = new Event(deviceId, "BUTTON", EventStatus.WAITING_AUDIO, firstAt.plusSeconds(70));
        session.recordImageReception(firstAt.plusSeconds(70), 1);
        session.complete(firstAt.plusSeconds(80));
        session = events.saveAndFlush(session);
        service.rememberCompletedEvent(session, firstAt.plusSeconds(80));
        var state = states.findById(deviceId).orElseThrow();
        assertEquals(session.getEventId(), state.getPackageEventId());
        assertEquals(firstAt, state.getFirstSeenAt());
        assertEquals(0, state.getMissCount());
        assertFalse(receive(4, firstAt.plusSeconds(140)).created());
    }

    @Test void sessionWithoutPackageDoesNotClearExistingState() {
        var first = receive(1, firstAt);
        Event session = new Event(deviceId, "BUTTON", EventStatus.COMPLETED, firstAt);
        session.recordImageReception(firstAt, 0);
        session = events.saveAndFlush(session);
        service.rememberCompletedEvent(session, firstAt.plusSeconds(1));
        assertEquals(first.event().getEventId(), states.findById(deviceId).orElseThrow().getPackageEventId());
    }

    @Test void legacyCountRowsAreReadAsPresentWithZeroMisses() {
        var first = receive(1, firstAt);
        var state = states.findById(deviceId).orElseThrow();
        ReflectionTestUtils.setField(state, "packagePresent", null);
        ReflectionTestUtils.setField(state, "missCount", null);
        ReflectionTestUtils.setField(state, "legacyPackageCount", 3);
        assertTrue(state.getPackagePresent());
        assertEquals(0, state.getMissCount());
        assertFalse(receive(1, firstAt.plusSeconds(61)).created());
        assertEquals(first.event().getEventId(), state.getPackageEventId());
    }

    private PackageReceptionService.ReceptionResult receive(int count, Instant at) {
        var vision = new VisionResponse(IntStream.range(0, count)
                .mapToObj(i -> new VisionResponse.Detection("package", .95)).toList(), List.of());
        var metadata = new DeviceEventMetadata(deviceId, "TOF", 1850, at.atOffset(ZoneOffset.UTC));
        return service.receive(metadata, classifier.classify("TOF", vision), "photo.jpg", "{}", at);
    }
}
