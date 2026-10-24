package com.datacat.server.push;

import com.datacat.server.event.Event;
import com.datacat.server.event.EventStatus;
import com.google.api.client.json.gson.GsonFactory;
import com.google.firebase.messaging.FirebaseMessaging;
import com.google.firebase.messaging.FirebaseMessagingException;
import com.google.firebase.messaging.Message;
import com.google.firebase.messaging.MessagingErrorCode;
import com.jayway.jsonpath.JsonPath;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.core.task.TaskExecutor;

import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.concurrent.RejectedExecutionException;

import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;

class VisitPushServiceTests {

    private PushTokenRepository repository;
    private FirebaseMessaging messaging;
    private TaskExecutor executor;
    private VisitPushService service;
    private Event event;
    private PushToken token;

    @BeforeEach
    void setUp() {
        repository = mock(PushTokenRepository.class);
        messaging = mock(FirebaseMessaging.class);
        executor = mock(TaskExecutor.class);

        service = new VisitPushService(
                repository,
                Optional.of(messaging),
                executor
        );

        token = new PushToken(
                "test-token-id-1",
                "test-fcm-token",
                "ANDROID",
                Instant.now()
        );

        when(repository.findAll()).thenReturn(List.of(token));

        event = mock(Event.class);

        when(event.getEventId()).thenReturn(101L);
        when(event.getStatus()).thenReturn(EventStatus.WAITING_AUDIO);
    }

    @Test
    void enqueuesMessageWithRequiredPayload() throws Exception {
        when(event.getNeedsReview()).thenReturn(true);

        service.notifyVisit(event);

        // 작업을 등록한 시점에는 DB 조회나 FCM 통신을 하지 않는다.
        verify(repository, never()).findAll();
        verifyNoInteractions(messaging);

        runQueuedTask();

        String json = sentMessageJson();

        assertEquals(
                "VISIT_EVENT",
                JsonPath.read(json, "$.data.type")
        );

        assertEquals(
                "101",
                JsonPath.read(json, "$.data.eventId")
        );

        assertEquals(
                "event_101",
                JsonPath.read(json, "$.data.tag")
        );

        assertEquals(
                "event_101",
                JsonPath.read(json, "$.android.collapse_key")
        );

        assertEquals(
                "event_101",
                JsonPath.read(json, "$.android.notification.tag")
        );

        assertEquals(
                "방문객이 왔어요",
                JsonPath.read(json, "$.notification.title")
        );

        assertEquals(
                "용건을 듣고 있어요 (확인 필요)",
                JsonPath.read(json, "$.notification.body")
        );
    }

    @Test
    void keepsMessageSnapshotUntilTaskRuns() throws Exception {
        service.notifyVisit(event);

        // 대기 중 원본 이벤트가 바뀌는 상황을 가정한다.
        when(event.getStatus()).thenReturn(EventStatus.COMPLETED);
        when(event.getSummary()).thenReturn("음성 분석 완료");

        runQueuedTask();

        assertEquals(
                "방문객이 왔어요",
                JsonPath.read(sentMessageJson(), "$.notification.title")
        );
    }

    @Test
    void formatsPackageNotification() {
        when(event.getStatus()).thenReturn(EventStatus.COMPLETED);
        when(event.getMainCategory()).thenReturn("물품만 있음");
        when(event.getReason()).thenReturn("물품 추가 (1개 → 2개)");

        VisitPushMessage message = VisitPushMessage.from(event);

        assertEquals("물품 도착", message.title());
        assertEquals("물품 추가 (1개 → 2개)", message.body());
    }

    @Test
    void skipsWhenFirebaseIsDisabled() {
        VisitPushService disabledService = new VisitPushService(
                repository,
                Optional.empty(),
                executor
        );

        disabledService.notifyVisit(event);

        verifyNoInteractions(executor, messaging);
        verify(repository, never()).findAll();
    }

    @Test
    void queueRejectionDoesNotEscapeToCaller() {
        doThrow(new RejectedExecutionException("테스트용 대기열 초과"))
                .when(executor)
                .execute(any(Runnable.class));

        assertDoesNotThrow(() -> service.notifyVisit(event));

        verifyNoInteractions(messaging);
        verify(repository, never()).findAll();
    }

    @Test
    void removesUnregisteredToken() throws Exception {
        FirebaseMessagingException error =
                mock(FirebaseMessagingException.class);

        when(error.getMessagingErrorCode())
                .thenReturn(MessagingErrorCode.UNREGISTERED);

        when(messaging.send(any(Message.class)))
                .thenThrow(error);

        service.notifyVisit(event);
        runQueuedTask();

        verify(repository).deleteById(token.getTokenId());
    }

    @Test
    void invalidArgumentKeepsTokenAndContinuesSending() throws Exception {
        PushToken secondToken = new PushToken(
                "test-token-id-2",
                "another-test-fcm-token",
                "ANDROID",
                Instant.now()
        );

        when(repository.findAll())
                .thenReturn(List.of(token, secondToken));

        FirebaseMessagingException error =
                mock(FirebaseMessagingException.class);

        when(error.getMessagingErrorCode())
                .thenReturn(MessagingErrorCode.INVALID_ARGUMENT);

        when(messaging.send(any(Message.class)))
                .thenThrow(error)
                .thenReturn("test-message-id");

        service.notifyVisit(event);
        runQueuedTask();

        verify(messaging, times(2)).send(any(Message.class));
        verify(repository, never()).deleteById(anyString());
    }

    private void runQueuedTask() {
        ArgumentCaptor<Runnable> captor =
                ArgumentCaptor.forClass(Runnable.class);

        verify(executor).execute(captor.capture());

        // 테스트 안에서 등록된 작업을 실행한다.
        captor.getValue().run();
    }

    private String sentMessageJson() throws Exception {
        ArgumentCaptor<Message> captor =
                ArgumentCaptor.forClass(Message.class);

        verify(messaging).send(captor.capture());

        return GsonFactory.getDefaultInstance()
                .toString(captor.getValue());
    }
}