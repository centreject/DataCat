package com.datacat.server.device;

import com.datacat.server.event.Event;
import com.datacat.server.event.EventExceptionHandler;
import com.datacat.server.event.EventRepository;
import com.datacat.server.event.EventStatus;
import com.datacat.server.push.VisitPushService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.context.bean.override.mockito.MockitoSpyBean;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.ResultActions;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;
import org.springframework.transaction.support.TransactionSynchronizationManager;

import java.time.Instant;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest
@ActiveProfiles("test")
class DeviceSessionEndTests {

    @Autowired
    private DeviceEventService deviceEventService;

    @Autowired
    private EventRepository eventRepository;

    @Autowired
    private DevicePackageStateRepository packageStateRepository;

    @MockitoBean
    private VisitPushService visitPushService;

    @MockitoSpyBean
    private PackageReceptionService packageReceptionService;

    private MockMvc mockMvc;
    private String deviceId;

    private final Instant startedAt = Instant.parse("2026-10-22T05:00:00Z");
    private final Instant endedAt = startedAt.plusSeconds(20);

    @BeforeEach
    void setUp() {
        deviceId = "end-test-" + UUID.randomUUID();
        mockMvc = MockMvcBuilders
                .standaloneSetup(new DeviceEventController(deviceEventService))
                .setControllerAdvice(new EventExceptionHandler())
                .build();
    }

    @Test
    void endsVisitUsingPackageSeenAndPushesAfterCommit() throws Exception {
        Event event = waitingEvent(2, false);
        event.recordImageReception(startedAt.plusSeconds(5), 0);
        eventRepository.saveAndFlush(event);

        doAnswer(invocation -> {
            assertFalse(TransactionSynchronizationManager.isActualTransactionActive());
            Event committed = reload(event);
            assertEquals(EventStatus.COMPLETED, committed.getStatus());
            assertTrue(packageStateRepository.existsById(deviceId));
            return null;
        }).when(visitPushService).notifyVisit(any(Event.class));

        end(event.getEventId(), "VISITOR_LEFT", endedAt)
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.eventId").value(event.getEventId().intValue()))
                .andExpect(jsonPath("$.status").value("COMPLETED"))
                .andExpect(jsonPath("$.action").value("END_SESSION"))
                .andExpect(jsonPath("$.preset").doesNotExist());

        Event saved = reload(event);
        assertEquals("UNATTENDED_DELIVERY", saved.getEventType());
        assertEquals("물품만 있음", saved.getMainCategory());
        assertEquals("무응답", saved.getProcessingStatus());
        assertEquals("안내 전 이탈", saved.getReason());
        assertEquals(endedAt, saved.getEndedAt());
        assertEquals(2, saved.getMaxPackageCount());

        DevicePackageState state = packageStateRepository.findById(deviceId).orElseThrow();
        assertTrue(state.getPackagePresent());
        assertEquals(event.getEventId(), state.getPackageEventId());
        verify(visitPushService, times(1)).notifyVisit(any(Event.class));
    }

    @Test
    void timeoutWithoutPackagePreservesReviewFlag() throws Exception {
        Event event = waitingEvent(0, true);

        end(event.getEventId(), "TIMEOUT", endedAt)
                .andExpect(status().isOk());

        Event saved = reload(event);
        assertEquals("VISITOR_TIMEOUT", saved.getEventType());
        assertEquals("기타·판단 불가", saved.getMainCategory());
        assertEquals("무응답", saved.getResponsePolicy());
        assertEquals("무응답", saved.getProcessingStatus());
        assertEquals("발화 없이 시간 초과", saved.getReason());
        assertTrue(saved.getNeedsReview());
        assertFalse(packageStateRepository.existsById(deviceId));
    }

    @Test
    void repeatedEndDoesNotRewriteResultOrSendAnotherPush() throws Exception {
        Event event = waitingEvent(0, false);

        end(event.getEventId(), "VISITOR_LEFT", endedAt).andExpect(status().isOk());
        end(event.getEventId(), "TIMEOUT", endedAt.plusSeconds(1)).andExpect(status().isOk());

        Event saved = reload(event);
        assertEquals(endedAt, saved.getEndedAt());
        assertEquals("안내 전 이탈", saved.getReason());
        verify(visitPushService, times(1)).notifyVisit(any(Event.class));
    }

    @Test
    void lateEndDoesNotOverwriteCompletedVoiceClassification() throws Exception {
        Event event = waitingEvent(0, false);
        event.applyClassification(
                "VISITOR_ACCEPTED", "개인 방문", null,
                "일반 접수", "정상", "용건: 개인 방문", false
        );
        Instant completedAt = startedAt.plusSeconds(10);
        event.complete(completedAt);
        eventRepository.saveAndFlush(event);

        end(event.getEventId(), "TIMEOUT", endedAt)
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.action").value("END_SESSION"));

        Event saved = reload(event);
        assertEquals("VISITOR_ACCEPTED", saved.getEventType());
        assertEquals("개인 방문", saved.getMainCategory());
        assertEquals(completedAt, saved.getEndedAt());
        verifyNoInteractions(visitPushService);
    }

    @Test
    void missingEventReturnsNotFound() throws Exception {
        end(Long.MAX_VALUE, "TIMEOUT", endedAt)
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.code").value("NOT_FOUND"));
        verifyNoInteractions(visitPushService);
    }

    @Test
    void invalidReasonReturnsBadRequestWithoutChangingEvent() throws Exception {
        Event event = waitingEvent(0, false);
        end(event.getEventId(), "DEVICE_CANCELLED", endedAt)
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value("INVALID_REQUEST"));
        assertEquals(EventStatus.WAITING_AUDIO, reload(event).getStatus());
        verifyNoInteractions(visitPushService);
    }

    @Test
    void missingEndTimeReturnsBadRequest() throws Exception {
        Event event = waitingEvent(0, false);
        mockMvc.perform(post("/api/v1/device/events/{eventId}/end", event.getEventId())
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"reason\":\"TIMEOUT\"}"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value("INVALID_REQUEST"));
        assertEquals(EventStatus.WAITING_AUDIO, reload(event).getStatus());
        verifyNoInteractions(visitPushService);
    }

    @Test
    void failedEventReturnsConflict() throws Exception {
        Event event = eventRepository.saveAndFlush(
                new Event(deviceId, "BUTTON", EventStatus.FAILED, startedAt)
        );
        end(event.getEventId(), "TIMEOUT", endedAt)
                .andExpect(status().isConflict())
                .andExpect(jsonPath("$.code").value("EVENT_STATE_CONFLICT"));
        assertEquals(EventStatus.FAILED, reload(event).getStatus());
        verifyNoInteractions(visitPushService);
    }

    @Test
    void endBeforeVisitTimeReturnsBadRequest() throws Exception {
        Event event = waitingEvent(0, false);
        end(event.getEventId(), "TIMEOUT", startedAt.minusSeconds(1))
                .andExpect(status().isBadRequest());
        assertEquals(EventStatus.WAITING_AUDIO, reload(event).getStatus());
        verifyNoInteractions(visitPushService);
    }

    @Test
    void packageStateFailureRollsBackEventAndSkipsPush() throws Exception {
        Event event = waitingEvent(1, false);
        doThrow(new IllegalStateException("테스트용 물품 상태 저장 실패"))
                .when(packageReceptionService)
                .rememberCompletedEvent(any(Event.class), any(Instant.class));

        end(event.getEventId(), "VISITOR_LEFT", endedAt)
                .andExpect(status().isInternalServerError());

        Event saved = reload(event);
        assertEquals(EventStatus.WAITING_AUDIO, saved.getStatus());
        assertNull(saved.getEndedAt());
        assertNull(saved.getEventType());
        assertFalse(packageStateRepository.existsById(deviceId));
        verifyNoInteractions(visitPushService);
    }

    @Test
    void newSessionEndUpdatesPackageEventWithoutDependingOnCount() throws Exception {
        Event original = waitingEvent(3, false);
        original.complete(startedAt.plusSeconds(1));
        eventRepository.saveAndFlush(original);
        packageStateRepository.saveAndFlush(
                new DevicePackageState(deviceId, original.getEventId(), startedAt)
        );
        Event next = waitingEvent(1, false);

        end(next.getEventId(), "TIMEOUT", endedAt).andExpect(status().isOk());

        DevicePackageState state = packageStateRepository.findById(deviceId).orElseThrow();
        assertTrue(state.getPackagePresent());
        assertEquals(0, state.getMissCount());
        assertEquals(next.getEventId(), state.getPackageEventId());
        assertEquals(startedAt, state.getFirstSeenAt());
        assertTrue(state.getLastSeenAt().isAfter(startedAt));
    }

    private Event waitingEvent(int packageCount, boolean needsReview) {
        Event event = new Event(deviceId, "BUTTON", EventStatus.WAITING_AUDIO, startedAt);
        event.recordImageReception(startedAt, packageCount);
        event.applyClassification(null, null, null, "일반 접수", "정상", "음성 대기", needsReview);
        return eventRepository.saveAndFlush(event);
    }

    private Event reload(Event event) {
        return eventRepository.findById(event.getEventId()).orElseThrow();
    }

    private ResultActions end(Long eventId, String reason, Instant endTime) throws Exception {
        String json = """
                {"reason":"%s","endedAt":"%s"}
                """.formatted(reason, endTime);
        return mockMvc.perform(post("/api/v1/device/events/{eventId}/end", eventId)
                .contentType(MediaType.APPLICATION_JSON)
                .content(json));
    }
}
