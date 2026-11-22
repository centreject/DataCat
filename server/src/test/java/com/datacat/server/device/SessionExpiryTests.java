package com.datacat.server.device;

import com.datacat.server.event.Event;
import com.datacat.server.event.EventRepository;
import com.datacat.server.event.EventStatus;
import com.datacat.server.model.AudioModelClient;
import com.datacat.server.model.AudioProcessResponse;
import com.datacat.server.push.VisitPushService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.transaction.support.TransactionSynchronizationManager;
import org.springframework.web.server.ResponseStatusException;

import java.time.Instant;
import java.util.List;
import java.util.UUID;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

@SpringBootTest
@ActiveProfiles("test")
class SessionExpiryTests {
    @Autowired EventRepository events;
    @Autowired DeviceEventService service;
    @Autowired DeviceSessionEndService ends;
    @Autowired DeviceSessionAudioService audio;
    @Autowired DevicePackageStateRepository packages;
    @MockitoBean VisitPushService push;
    @MockitoBean AudioModelClient model;

    private final Instant now = Instant.parse("2026-11-08T10:00:00Z");

    @BeforeEach
    void clean() {
        packages.deleteAll();
        events.deleteAll();
    }

    private Event waiting(Instant at) {
        return events.saveAndFlush(new Event("expiry-" + UUID.randomUUID(), "TOF",
                EventStatus.WAITING_AUDIO, at));
    }

    private Event reload(Event event) { return events.findById(event.getEventId()).orElseThrow(); }

    @Test
    void expiresLegacyWaitingSessionAtBoundaryButKeepsRecentAndCompleted() {
        Event old = waiting(now.minusSeconds(120)); // 예전 DB: 활동·사진 시각 null
        Event recent = waiting(now.minusSeconds(119));
        Event completed = waiting(now.minusSeconds(200));
        completed.complete(now.minusSeconds(100));
        events.saveAndFlush(completed);
        assertEquals(1, ends.expireInactive(now.minusSeconds(120), now).size());
        assertEquals(EventStatus.COMPLETED, reload(old).getStatus());
        assertEquals("후속 요청 없이 세션 대기 시간 초과", reload(old).getReason());
        assertTrue(reload(old).getNeedsReview());
        assertEquals(EventStatus.WAITING_AUDIO, reload(recent).getStatus());
        assertEquals(now.minusSeconds(100), reload(completed).getEndedAt());
    }

    @Test
    void latestPhotoRestartsDeadline() {
        Event event = waiting(now.minusSeconds(300));
        event.recordImageReception(now.minusSeconds(10), 0);
        events.saveAndFlush(event);
        assertTrue(ends.expireInactive(now.minusSeconds(120), now).isEmpty());
    }

    @Test
    void audioArrivalRestartsDeadlineEvenBeforeModelRetry() {
        Event event = waiting(now.minusSeconds(300));
        audio.prepare(event.getEventId(), "a".repeat(64), now.minusSeconds(10));
        assertTrue(ends.expireInactive(now.minusSeconds(120), now).isEmpty());
    }

    @Test
    void sendsOnePushAfterCommitAndRejectsLateAudio() {
        Event event = waiting(Instant.now().minusSeconds(300));
        doAnswer(call -> {
            assertFalse(TransactionSynchronizationManager.isActualTransactionActive());
            assertEquals(EventStatus.COMPLETED, reload(event).getStatus());
            return null;
        }).when(push).notifyVisit(any(Event.class));
        assertEquals(1, service.expireInactiveSessions(120_000));
        assertEquals(0, service.expireInactiveSessions(120_000));
        verify(push, times(1)).notifyVisit(any(Event.class));
        var failure = assertThrows(ResponseStatusException.class,
                () -> audio.prepare(event.getEventId(), "a".repeat(64), Instant.now()));
        assertEquals(409, failure.getStatusCode().value());
    }

    @Test
    void expiryDoesNotReplaceNewerPackageObservation() {
        Event old = waiting(now.minusSeconds(300));
        old.recordImageReception(now.minusSeconds(300), 1);
        events.saveAndFlush(old);
        Event newer = new Event(old.getDeviceId(), "TOF", EventStatus.COMPLETED, now);
        events.saveAndFlush(newer);
        packages.saveAndFlush(new DevicePackageState(old.getDeviceId(), newer.getEventId(), now));
        ends.expireInactive(now.minusSeconds(120), now);
        assertEquals(newer.getEventId(), packages.findById(old.getDeviceId()).orElseThrow().getPackageEventId());
    }

    @Test
    void timerCannotCloseSessionDuringActiveModelCall() throws Exception {
        Event event = waiting(Instant.now().minusSeconds(300));
        CountDownLatch entered = new CountDownLatch(1);
        CountDownLatch release = new CountDownLatch(1);
        when(model.process(any())).thenAnswer(call -> {
            entered.countDown();
            assertTrue(release.await(5, TimeUnit.SECONDS));
            return new AudioProcessResponse("택배입니다", "DELIVERY", "PARCEL", "택배 도착", List.of());
        });
        try (var executor = Executors.newFixedThreadPool(2)) {
            var response = executor.submit(() -> service.receiveAudio(event.getEventId(),
                    new MockMultipartFile("audio", "test.wav", "audio/wav", new byte[]{1, 2})));
            try {
                assertTrue(entered.await(5, TimeUnit.SECONDS));
                var expiry = executor.submit(() -> service.expireInactiveSessions(1));
                assertThrows(TimeoutException.class, () -> expiry.get(100, TimeUnit.MILLISECONDS));
                release.countDown();
                assertEquals(EventStatus.COMPLETED, response.get(5, TimeUnit.SECONDS).status());
                assertEquals(0, expiry.get(5, TimeUnit.SECONDS));
            } finally {
                release.countDown();
            }
        }
        assertEquals("DELIVERY", reload(event).getPurpose());
    }
}
