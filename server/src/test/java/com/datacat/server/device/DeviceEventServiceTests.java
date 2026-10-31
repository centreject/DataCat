package com.datacat.server.device;

import com.datacat.server.classification.ImageClassificationService;
import com.datacat.server.event.Event;
import com.datacat.server.event.EventStatus;
import com.datacat.server.model.AudioModelClient;
import com.datacat.server.model.VisionModelClient;
import com.datacat.server.model.VisionResponse;
import com.datacat.server.push.VisitPushService;
import com.datacat.server.storage.SnapshotStorageService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpStatus;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.test.util.ReflectionTestUtils;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.server.ResponseStatusException;
import tools.jackson.databind.ObjectMapper;

import java.time.Instant;
import java.time.OffsetDateTime;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

class DeviceEventServiceTests {
    private DeviceSessionImageService images;
    private SnapshotStorageService storage;
    private VisionModelClient vision;
    private VisitPushService push;
    private DeviceEventService service;
    private final ImageClassificationService classifier = new ImageClassificationService();

    @BeforeEach void setUp() {
        images = mock(DeviceSessionImageService.class);
        storage = mock(SnapshotStorageService.class);
        vision = mock(VisionModelClient.class);
        push = mock(VisitPushService.class);
        ObjectMapper mapper = mock(ObjectMapper.class);
        when(mapper.writeValueAsString(any(VisionResponse.class))).thenReturn("{}");
        when(storage.save(any(MultipartFile.class))).thenReturn("new.jpg");
        when(vision.detect(any(MultipartFile.class))).thenReturn(packageVision());
        service = new DeviceEventService(images, storage, vision, classifier, mapper, push,
                mock(DeviceSessionEndService.class), mock(AudioModelClient.class),
                mock(DeviceSessionAudioService.class));
    }

    @Test void requestsPushOnlyAfterImageSaveReturns() {
        Event event = event(packageVision());
        saved(event, true, true, "old.jpg", true);
        var result = service.createEvent(metadata(), image());
        assertTrue(result.created());
        assertEquals(DeviceAction.SILENT_STANDBY, result.response().action());
        var order = inOrder(images, storage, push);
        order.verify(images).save(any(), any(), eq("new.jpg"), eq("{}"), any());
        order.verify(storage).delete("old.jpg");
        order.verify(push).notifyVisit(event);
    }

    @Test void duplicatePackageDiscardsNewPhotoWithoutDeletingStoredPhotoOrPushing() {
        Event event = event(packageVision());
        saved(event, false, false, null, false);
        var result = service.createEvent(metadata(), image());
        assertFalse(result.created());
        assertEquals(99L, result.response().eventId());
        verify(storage).delete("new.jpg");
        verify(storage, never()).delete("old.jpg");
        verifyNoInteractions(push);
    }

    @Test void modelFailureUsesA0AndStillStartsReception() {
        when(vision.detect(any())).thenThrow(new ResponseStatusException(HttpStatus.SERVICE_UNAVAILABLE, "모델 장애"));
        Event event = new Event("door", "TOF", EventStatus.WAITING_AUDIO, Instant.now());
        event.applyImageClassification(classifier.modelUnavailable(), Instant.now());
        saved(event, true, true, null, true);
        var result = service.createEvent(metadata(), image());
        assertEquals(DeviceAction.START_RECEPTION, result.response().action());
        verify(images).save(any(), argThat(c -> "A0".equals(c.ruleId())), eq("new.jpg"), isNull(), any());
        verify(push).notifyVisit(event);
    }

    @Test void failedSaveCleansNewPhotoAndSkipsPush() {
        when(images.save(any(), any(), anyString(), any(), any()))
                .thenThrow(new IllegalStateException("DB 저장 실패"));
        assertThrows(IllegalStateException.class, () -> service.createEvent(metadata(), image()));
        verify(storage).delete("new.jpg");
        verifyNoInteractions(push);
    }

    @Test void noVisitorDoesNotPush() {
        VisionResponse empty = new VisionResponse(List.of(), List.of());
        when(vision.detect(any())).thenReturn(empty);
        saved(event(empty), true, false, null, true);
        service.createEvent(metadata(), image());
        verifyNoInteractions(push);
    }

    @Test void cleanupFailureAfterCommitDoesNotDeleteCurrentPhotoOrFailRequest() {
        Event event = event(packageVision());
        saved(event, true, true, "old.jpg", true);
        doThrow(new IllegalStateException("이전 파일 정리 실패")).when(storage).delete("old.jpg");
        assertDoesNotThrow(() -> service.createEvent(metadata(), image()));
        verify(storage, never()).delete("new.jpg");
        verify(push).notifyVisit(event);
    }

    @Test void invalidMetadataIsRejectedBeforeSideEffects() {
        var bad = new DeviceEventMetadata("", "TOF", 100, OffsetDateTime.now());
        assertEquals(400, assertThrows(ResponseStatusException.class,
                () -> service.createEvent(bad, image())).getStatusCode().value());
        verifyNoInteractions(storage, vision, images, push);
    }

    private void saved(Event event, boolean created, boolean notify, String previous, boolean used) {
        when(images.save(any(), any(), anyString(), any(), any()))
                .thenReturn(new DeviceSessionImageService.ImageSaveResult(event, created, notify, previous, used));
    }
    private Event event(VisionResponse response) {
        Event event = new Event("door", "TOF", EventStatus.WAITING_AUDIO, Instant.now());
        ReflectionTestUtils.setField(event, "eventId", 99L);
        event.attachSnapshot("old.jpg");
        event.applyImageClassification(classifier.classify("TOF", response), Instant.now());
        return event;
    }
    private DeviceEventMetadata metadata() {
        return new DeviceEventMetadata("door", "TOF", 1850, OffsetDateTime.now());
    }
    private MultipartFile image() {
        return new MockMultipartFile("image", "package.jpg", "image/jpeg", new byte[]{1});
    }
    private VisionResponse packageVision() {
        return new VisionResponse(List.of(new VisionResponse.Detection("package", .95)), List.of());
    }
}
