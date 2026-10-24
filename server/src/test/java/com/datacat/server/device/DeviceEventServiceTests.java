package com.datacat.server.device;

import com.datacat.server.classification.ImageClassificationService;
import com.datacat.server.event.Event;
import com.datacat.server.event.EventRepository;
import com.datacat.server.event.EventStatus;
import com.datacat.server.model.VisionModelClient;
import com.datacat.server.model.VisionResponse;
import com.datacat.server.push.VisitPushService;
import com.datacat.server.storage.SnapshotStorageService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.mockito.InOrder;
import org.springframework.http.HttpStatus;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.server.ResponseStatusException;
import tools.jackson.databind.ObjectMapper;

import java.time.Instant;
import java.time.OffsetDateTime;
import java.util.List;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

class DeviceEventServiceTests {

    private EventRepository eventRepository;
    private SnapshotStorageService snapshotStorageService;
    private VisionModelClient visionModelClient;
    private VisitPushService visitPushService;

    private ImageClassificationService classificationService;
    private DeviceEventService service;

    @BeforeEach
    void setUp() {
        // 외부 저장소와 모델, 푸시를 테스트용 가짜 객체로 만든다.
        eventRepository = mock(EventRepository.class);
        snapshotStorageService = mock(SnapshotStorageService.class);
        visionModelClient = mock(VisionModelClient.class);
        visitPushService = mock(VisitPushService.class);

        // 분류 로직은 실제 코드를 사용한다.
        classificationService = new ImageClassificationService();

        ObjectMapper objectMapper = mock(ObjectMapper.class);

        service = new DeviceEventService(
                eventRepository,
                snapshotStorageService,
                visionModelClient,
                classificationService,
                objectMapper,
                visitPushService
        );

        // 기본 상황: 병합할 기존 방문이 없다.
        when(eventRepository
                .findFirstByDeviceIdAndLastImageReceivedAtGreaterThanEqualOrderByLastImageReceivedAtDescEventIdDesc(
                        anyString(),
                        any(Instant.class)
                ))
                .thenReturn(Optional.empty());

        when(snapshotStorageService.save(any(MultipartFile.class)))
                .thenReturn("new.jpg");

        when(objectMapper.writeValueAsString(any(VisionResponse.class)))
                .thenReturn("{}");

        // DB 저장을 흉내 내고 전달받은 Event를 반환한다.
        when(eventRepository.saveAndFlush(any(Event.class)))
                .thenAnswer(invocation -> invocation.getArgument(0));
    }

    @Test
    @DisplayName("물품 방문을 저장한 다음 푸시를 요청한다")
    void packageDetectionSavesClassificationThenRequestsPush() {
        when(visionModelClient.detect(any(MultipartFile.class)))
                .thenReturn(packageVision());

        DeviceEventService.CreationResult result =
                service.createEvent(metadata(), image());

        Event saved = capturedEvent();

        assertAll(
                () -> assertEquals("A3", saved.getImageRuleId()),
                () -> assertEquals(
                        "UNATTENDED_DELIVERY",
                        saved.getEventType()
                ),
                () -> assertEquals(
                        "물품만 있음",
                        saved.getMainCategory()
                ),
                () -> assertEquals(
                        "무응답",
                        saved.getResponsePolicy()
                ),
                () -> assertEquals(
                        EventStatus.COMPLETED,
                        saved.getStatus()
                ),
                () -> assertEquals(1, saved.getMaxPackageCount()),
                () -> assertEquals(
                        DeviceAction.SILENT_STANDBY,
                        result.response().action()
                ),
                () -> assertTrue(result.created()),
                () -> assertTrue(result.notificationRequired())
        );

        // 저장 호출보다 푸시 요청이 먼저 실행되면 테스트가 실패한다.
        InOrder order = inOrder(eventRepository, visitPushService);

        order.verify(eventRepository).saveAndFlush(saved);
        order.verify(visitPushService).notifyVisit(saved);
    }

    @Test
    @DisplayName("우선순위가 낮은 사진은 기존 판정을 유지하고 푸시하지 않는다")
    void lowerPriorityPhotoKeepsPreviousClassification() {
        Instant previousTime = Instant.now().minusSeconds(5);

        Event previous = completedPackageEvent(previousTime);

        useExistingEvent(previous);

        when(visionModelClient.detect(any(MultipartFile.class)))
                .thenReturn(emptyVision());

        DeviceEventService.CreationResult result =
                service.createEvent(metadata(), image());

        assertAll(
                () -> assertEquals("A3", previous.getImageRuleId()),
                () -> assertEquals(
                        "UNATTENDED_DELIVERY",
                        previous.getEventType()
                ),
                () -> assertEquals(
                        EventStatus.COMPLETED,
                        previous.getStatus()
                ),
                () -> assertEquals(
                        previousTime,
                        previous.getEndedAt()
                ),
                () -> assertEquals(
                        1,
                        previous.getMaxPackageCount()
                ),
                () -> assertEquals(
                        "new.jpg",
                        previous.getSnapshotPath()
                ),
                () -> assertFalse(result.created()),
                () -> assertFalse(result.notificationRequired())
        );

        verify(snapshotStorageService).delete("old.jpg");
        verifyNoInteractions(visitPushService);
    }

    @Test
    @DisplayName("모델 장애 시 A0으로 접수하고 푸시를 요청한다")
    void modelFailureStartsReceptionWithA0() {
        when(visionModelClient.detect(any(MultipartFile.class)))
                .thenThrow(new ResponseStatusException(
                        HttpStatus.SERVICE_UNAVAILABLE,
                        "테스트용 모델 연결 실패"
                ));

        DeviceEventService.CreationResult result =
                service.createEvent(metadata(), image());

        Event saved = capturedEvent();

        assertAll(
                () -> assertEquals("A0", saved.getImageRuleId()),
                () -> assertEquals(
                        "이미지 판단 실패",
                        saved.getProcessingStatus()
                ),
                () -> assertEquals(
                        EventStatus.WAITING_AUDIO,
                        saved.getStatus()
                ),
                () -> assertTrue(saved.getNeedsReview()),
                () -> assertEquals(
                        DeviceAction.START_RECEPTION,
                        result.response().action()
                ),
                () -> assertTrue(result.notificationRequired())
        );

        verify(visitPushService).notifyVisit(saved);
    }

    @Test
    @DisplayName("DB 저장 실패 시 새 사진을 정리하고 푸시하지 않는다")
    void databaseFailureCleansUpNewPhotoWithoutPush() {
        when(visionModelClient.detect(any(MultipartFile.class)))
                .thenReturn(packageVision());

        IllegalStateException failure =
                new IllegalStateException("테스트용 DB 저장 실패");

        when(eventRepository.saveAndFlush(any(Event.class)))
                .thenThrow(failure);

        IllegalStateException actual = assertThrows(
                IllegalStateException.class,
                () -> service.createEvent(metadata(), image())
        );

        assertSame(failure, actual);

        verify(snapshotStorageService).delete("new.jpg");
        verifyNoInteractions(visitPushService);
    }

    @Test
    @DisplayName("사람과 물품이 없는 A5 방문은 푸시하지 않는다")
    void noVisitorDoesNotRequestPush() {
        when(visionModelClient.detect(any(MultipartFile.class)))
                .thenReturn(emptyVision());

        DeviceEventService.CreationResult result =
                service.createEvent(metadata(), image());

        Event saved = capturedEvent();

        assertAll(
                () -> assertEquals("A5", saved.getImageRuleId()),
                () -> assertEquals(
                        EventStatus.COMPLETED,
                        saved.getStatus()
                ),
                () -> assertEquals(
                        DeviceAction.SILENT_STANDBY,
                        result.response().action()
                ),
                () -> assertTrue(result.created()),
                () -> assertFalse(result.notificationRequired())
        );

        verifyNoInteractions(visitPushService);
    }

    @Test
    @DisplayName("기존 물품 방문에서 사람이 감지되면 판정을 갱신하고 푸시한다")
    void higherPriorityPhotoUpdatesClassificationAndRequestsPush() {
        Event previous = completedPackageEvent(
                Instant.now().minusSeconds(5)
        );

        useExistingEvent(previous);

        when(visionModelClient.detect(any(MultipartFile.class)))
                .thenReturn(personVision());

        DeviceEventService.CreationResult result =
                service.createEvent(metadata(), image());

        assertAll(
                () -> assertEquals("A1", previous.getImageRuleId()),
                () -> assertEquals(
                        EventStatus.WAITING_AUDIO,
                        previous.getStatus()
                ),
                () -> assertNull(previous.getEndedAt()),
                () -> assertEquals(
                        1,
                        previous.getMaxPackageCount()
                ),
                () -> assertEquals(
                        DeviceAction.START_RECEPTION,
                        result.response().action()
                ),
                () -> assertFalse(result.created()),
                () -> assertTrue(result.notificationRequired())
        );

        verify(eventRepository).saveAndFlush(previous);
        verify(visitPushService).notifyVisit(previous);
        verify(snapshotStorageService).delete("old.jpg");
    }

    private Event completedPackageEvent(Instant time) {
        Event event = new Event(
                "test-door-01",
                "TOF",
                EventStatus.WAITING_AUDIO,
                time
        );

        event.recordImageReception(time, 1);
        event.attachSnapshot("old.jpg");

        event.applyImageClassification(
                classificationService.classify(
                        "TOF",
                        packageVision()
                ),
                time
        );

        return event;
    }

    private void useExistingEvent(Event event) {
        when(eventRepository
                .findFirstByDeviceIdAndLastImageReceivedAtGreaterThanEqualOrderByLastImageReceivedAtDescEventIdDesc(
                        anyString(),
                        any(Instant.class)
                ))
                .thenReturn(Optional.of(event));
    }

    private Event capturedEvent() {
        ArgumentCaptor<Event> captor =
                ArgumentCaptor.forClass(Event.class);

        verify(eventRepository).saveAndFlush(captor.capture());

        return captor.getValue();
    }

    private DeviceEventMetadata metadata() {
        return new DeviceEventMetadata(
                "test-door-01",
                "TOF",
                1850,
                OffsetDateTime.now()
        );
    }

    private MultipartFile image() {
        // 파일 검증과 저장은 가짜 저장 서비스가 대신한다.
        return new MockMultipartFile(
                "image",
                "package.jpg",
                "image/jpeg",
                new byte[]{1}
        );
    }

    private VisionResponse packageVision() {
        return new VisionResponse(
                List.of(
                        new VisionResponse.Detection(
                                "package",
                                0.95
                        )
                ),
                List.of()
        );
    }

    private VisionResponse personVision() {
        return new VisionResponse(
                List.of(
                        new VisionResponse.Detection(
                                "person",
                                0.95
                        )
                ),
                List.of()
        );
    }

    private VisionResponse emptyVision() {
        return new VisionResponse(
                List.of(),
                List.of()
        );
    }
}