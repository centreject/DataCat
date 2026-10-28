package com.datacat.server.device;

import com.datacat.server.classification.ImageClassificationResult;
import com.datacat.server.classification.ImageClassificationService;
import com.datacat.server.event.Event;
import com.datacat.server.event.EventController;
import com.datacat.server.event.EventExceptionHandler;
import com.datacat.server.event.EventRepository;
import com.datacat.server.event.EventStatus;
import com.datacat.server.model.AudioModelClient;
import com.datacat.server.model.AudioProcessResponse;
import com.datacat.server.model.VisionResponse;
import com.datacat.server.push.VisitPushService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.context.bean.override.mockito.MockitoSpyBean;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.ResultActions;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;
import org.springframework.transaction.support.TransactionSynchronizationManager;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.server.ResponseStatusException;

import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;
import java.util.concurrent.CyclicBarrier;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.multipart;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest
@ActiveProfiles("test")
class DeviceSessionAudioTests {

    @Autowired private DeviceEventService deviceEventService;
    @Autowired private EventController eventController;
    @Autowired private EventRepository eventRepository;
    @Autowired private DevicePackageStateRepository packageStateRepository;
    @Autowired private ImageClassificationService imageClassificationService;

    @MockitoBean private AudioModelClient audioModelClient;
    @MockitoBean private VisitPushService visitPushService;
    @MockitoSpyBean private PackageReceptionService packageReceptionService;

    private MockMvc mockMvc;
    private String deviceId;
    private Instant photoAt;

    @BeforeEach
    void setUp() {
        deviceId = "audio-test-" + UUID.randomUUID();
        photoAt = Instant.now().minusSeconds(5).truncatedTo(ChronoUnit.MICROS);
        mockMvc = MockMvcBuilders
                .standaloneSetup(new DeviceEventController(deviceEventService), eventController)
                .setControllerAdvice(new EventExceptionHandler())
                .defaultResponseCharacterEncoding(StandardCharsets.UTF_8)
                .build();
        when(audioModelClient.process(any(MultipartFile.class))).thenReturn(delivery(List.of()));
    }

    @Test
    void savesAudioAndPackageStateThenPushesAfterCommit() throws Exception {
        Event event = waitingEvent(1, 2, false);

        when(audioModelClient.process(any(MultipartFile.class))).thenAnswer(invocation -> {
            assertFalse(TransactionSynchronizationManager.isActualTransactionActive());
            return delivery(List.of());
        });
        doAnswer(invocation -> {
            assertFalse(TransactionSynchronizationManager.isActualTransactionActive());
            assertEquals("DELIVERY", reload(event).getPurpose());
            assertTrue(packageStateRepository.existsById(deviceId));
            return null;
        }).when(visitPushService).notifyVisit(any(Event.class));

        upload(event.getEventId(), 1)
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.eventId").value(event.getEventId().intValue()))
                .andExpect(jsonPath("$.status").value("COMPLETED"))
                .andExpect(jsonPath("$.action").value("PLAY_PRESET"))
                .andExpect(jsonPath("$.preset.presetId").value(2))
                .andExpect(jsonPath("$.preset.text").value("접수되었습니다."))
                .andExpect(jsonPath("$.transcript").doesNotExist());

        Event saved = reload(event);
        assertEquals("택배 왔습니다. 문 앞에 놓고 갈게요.", saved.getTranscript());
        assertEquals("택배 문 앞 보관", saved.getSummary());
        assertEquals("DELIVERY", saved.getPurpose());
        assertEquals("PARCEL", saved.getSubtype());
        assertEquals("VISITOR_ACCEPTED", saved.getEventType());
        assertEquals("배송", saved.getMainCategory());
        assertEquals("택배", saved.getSubCategory());
        assertEquals("일반 접수", saved.getResponsePolicy());
        assertEquals("정상", saved.getProcessingStatus());
        assertEquals("용건: 배송(택배)", saved.getReason());
        assertFalse(saved.getNeedsReview());
        assertNotNull(saved.getEndedAt());
        assertEquals(64, saved.getAudioHash().length());
        assertEquals("existing.jpg", saved.getSnapshotPath());
        assertEquals(event.getOccurredAt(), saved.getOccurredAt());
        assertTrue(packageStateRepository.findById(deviceId).orElseThrow().getPackagePresent());
        assertEquals(0, packageStateRepository.findById(deviceId).orElseThrow().getMissCount());
        verify(visitPushService, times(1)).notifyVisit(any(Event.class));

        mockMvc.perform(get("/api/v1/events/{eventId}", event.getEventId()))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.purpose").value("DELIVERY"))
                .andExpect(jsonPath("$.mainCategory").value("배송"))
                .andExpect(jsonPath("$.subCategory").value("택배"))
                .andExpect(jsonPath("$.transcript").value(saved.getTranscript()))
                .andExpect(jsonPath("$.audioHash").doesNotExist());
    }

    @Test
    void savesNoSpeechAsCompletedUnansweredResult() throws Exception {
        Event event = waitingEvent(1, 0, false);
        when(audioModelClient.process(any(MultipartFile.class))).thenReturn(
                new AudioProcessResponse("", "UNKNOWN", null, "", List.of("NO_SPEECH"))
        );
        upload(event.getEventId(), 1).andExpect(status().isOk());
        Event saved = reload(event);
        assertEquals(EventStatus.COMPLETED, saved.getStatus());
        assertEquals("", saved.getTranscript());
        assertEquals("UNKNOWN", saved.getPurpose());
        assertEquals("무응답", saved.getProcessingStatus());
        assertFalse(saved.getNeedsReview());
    }

    @Test
    void preservesCameraReviewFlag() throws Exception {
        Event event = waitingEvent(1, 0, true);
        upload(event.getEventId(), 1).andExpect(status().isOk());
        assertTrue(reload(event).getNeedsReview());
        assertTrue(reload(event).getImageNeedsReview());
    }

    @Test
    void preservesImageModelFailure() throws Exception {
        Event event = new Event(deviceId, "BUTTON", EventStatus.WAITING_AUDIO, photoAt);
        event.recordImageReception(photoAt, null);
        event.applyImageClassification(imageClassificationService.modelUnavailable(), photoAt);
        event = eventRepository.saveAndFlush(event);
        upload(event.getEventId(), 1).andExpect(status().isOk());
        assertEquals("이미지 판단 실패", reload(event).getProcessingStatus());
        assertTrue(reload(event).getNeedsReview());
    }

    @Test
    void laterSuccessfulAnalysisClearsOnlyVoiceFallbackReview() throws Exception {
        // 새 컬럼이 비어 있는 기존 방문도 첫 음성 처리 전에 사진 정보를 보관한다.
        Event event = new Event(deviceId, "BUTTON", EventStatus.WAITING_AUDIO, photoAt);
        event.recordImageReception(photoAt, 0);
        event.applyClassification(null, null, null, "일반 접수", "정상", "음성 대기", false);
        event = eventRepository.saveAndFlush(event);
        when(audioModelClient.process(any(MultipartFile.class)))
                .thenReturn(delivery(List.of("RULES_FALLBACK")), delivery(List.of()));
        upload(event.getEventId(), 1).andExpect(status().isOk());
        assertTrue(reload(event).getNeedsReview());
        upload(event.getEventId(), 2).andExpect(status().isOk());
        assertFalse(reload(event).getNeedsReview());
        assertFalse(reload(event).getImageNeedsReview());
    }

    @Test
    void laterAnalysisRestoresOriginalMultipleVisitorStatus() throws Exception {
        Event event = waitingEvent(2, 0, false);
        when(audioModelClient.process(any(MultipartFile.class)))
                .thenReturn(delivery(List.of("RULES_FALLBACK")), delivery(List.of()));
        upload(event.getEventId(), 1).andExpect(status().isOk());
        assertEquals("정상", reload(event).getProcessingStatus());
        upload(event.getEventId(), 2).andExpect(status().isOk());
        assertEquals("복수 방문자", reload(event).getProcessingStatus());
        assertEquals("복수 방문자", reload(event).getImageProcessingStatus());
    }

    @Test
    void sameLastRecordingDoesNotRunModelOrPushTwice() throws Exception {
        Event event = waitingEvent(1, 0, false);
        upload(event.getEventId(), 1).andExpect(status().isOk());
        Instant firstEndedAt = reload(event).getEndedAt();
        mockMvc.perform(multipart("/api/v1/device/events/{eventId}/audio", event.getEventId())
                        .file(audio(1, "renamed.wav")))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.action").value("PLAY_PRESET"));
        assertEquals(firstEndedAt, reload(event).getEndedAt());
        verify(audioModelClient, times(1)).process(any(MultipartFile.class));
        verify(visitPushService, times(1)).notifyVisit(any(Event.class));
    }

    @Test
    void concurrentSameRecordingIsSavedOnceInSingleServer() throws Exception {
        Event event = waitingEvent(1, 0, false);
        CyclicBarrier barrier = new CyclicBarrier(2);
        ExecutorService executor = Executors.newFixedThreadPool(2);
        try {
            List<Future<Integer>> futures = new ArrayList<>();
            for (int i = 0; i < 2; i++) {
                futures.add(executor.submit(() -> {
                    barrier.await(5, TimeUnit.SECONDS);
                    return upload(event.getEventId(), 1).andReturn().getResponse().getStatus();
                }));
            }
            for (Future<Integer> future : futures) {
                assertEquals(200, future.get(10, TimeUnit.SECONDS));
            }
        } finally {
            executor.shutdownNow();
        }
        verify(audioModelClient, times(1)).process(any(MultipartFile.class));
        verify(visitPushService, times(1)).notifyVisit(any(Event.class));
    }

    @Test
    void differentRecordingInWindowUpdatesSameVisit() throws Exception {
        Event event = waitingEvent(1, 0, false);
        when(audioModelClient.process(any(MultipartFile.class)))
                .thenReturn(delivery(List.of()),
                        new AudioProcessResponse("반품 수거하러 왔습니다.", "PICKUP", null, "반품 수거", List.of()));
        upload(event.getEventId(), 1).andExpect(status().isOk());
        String firstHash = reload(event).getAudioHash();
        upload(event.getEventId(), 2).andExpect(status().isOk());
        Event saved = reload(event);
        assertEquals("PICKUP", saved.getPurpose());
        assertEquals("수거", saved.getMainCategory());
        assertNull(saved.getSubtype());
        assertNull(saved.getSubCategory());
        assertNotEquals(firstHash, saved.getAudioHash());
        verify(visitPushService, times(2)).notifyVisit(any(Event.class));
    }

    @Test
    void firstAudioCanArriveLateButAdditionalDifferentAudioUsesPhotoWindow() throws Exception {
        photoAt = Instant.now().minusSeconds(120).truncatedTo(ChronoUnit.MICROS);
        Event event = waitingEvent(1, 0, false);
        upload(event.getEventId(), 1).andExpect(status().isOk());
        upload(event.getEventId(), 1).andExpect(status().isOk());
        upload(event.getEventId(), 2).andExpect(status().isConflict())
                .andExpect(jsonPath("$.code").value("EVENT_STATE_CONFLICT"));
        verify(audioModelClient, times(1)).process(any(MultipartFile.class));
        verify(visitPushService, times(1)).notifyVisit(any(Event.class));
    }

    @Test
    void completedEndSessionRejectsLateAudio() throws Exception {
        Event event = waitingEvent(1, 0, false);
        event.applyClassification("VISITOR_TIMEOUT", "기타·판단 불가", null,
                "무응답", "무응답", "안내 전 이탈", false);
        event.complete(photoAt.plusSeconds(1));
        eventRepository.saveAndFlush(event);
        upload(event.getEventId(), 1).andExpect(status().isConflict());
        assertEquals("VISITOR_TIMEOUT", reload(event).getEventType());
        verifyNoInteractions(audioModelClient, visitPushService);
    }

    @Test
    void missingVisitReturns404WithoutModelCall() throws Exception {
        upload(Long.MAX_VALUE, 1).andExpect(status().isNotFound());
        verifyNoInteractions(audioModelClient, visitPushService);
    }

    @Test
    void nonPositiveIdReturns400() throws Exception {
        upload(0L, 1).andExpect(status().isBadRequest());
        verifyNoInteractions(audioModelClient, visitPushService);
    }

    @Test
    void failedVisitReturns409WithoutModelCall() throws Exception {
        Event event = eventRepository.saveAndFlush(
                new Event(deviceId, "BUTTON", EventStatus.FAILED, photoAt));
        upload(event.getEventId(), 1).andExpect(status().isConflict());
        verifyNoInteractions(audioModelClient, visitPushService);
    }

    @Test
    void missingAudioPartReturns400() throws Exception {
        Event event = waitingEvent(1, 0, false);
        mockMvc.perform(multipart("/api/v1/device/events/{eventId}/audio", event.getEventId()))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value("INVALID_REQUEST"));
        verifyNoInteractions(audioModelClient, visitPushService);
    }

    @Test
    void emptyAudioReturns400() throws Exception {
        Event event = waitingEvent(1, 0, false);
        mockMvc.perform(multipart("/api/v1/device/events/{eventId}/audio", event.getEventId())
                        .file(new MockMultipartFile("audio", "empty.wav", "audio/wav", new byte[0])))
                .andExpect(status().isBadRequest());
        verifyNoInteractions(audioModelClient, visitPushService);
    }

    @Test
    void oversizedAudioReturns400BeforeModelCall() throws Exception {
        Event event = waitingEvent(1, 0, false);
        mockMvc.perform(multipart("/api/v1/device/events/{eventId}/audio", event.getEventId())
                        .file(new MockMultipartFile("audio", "large.wav", "audio/wav",
                                new byte[16 * 1024 * 1024 + 1])))
                .andExpect(status().isBadRequest());
        verifyNoInteractions(audioModelClient, visitPushService);
    }

    @Test
    void modelBadRequestDoesNotSaveAudio() throws Exception {
        Event event = waitingEvent(1, 0, false);
        when(audioModelClient.process(any(MultipartFile.class)))
                .thenThrow(new ResponseStatusException(HttpStatus.BAD_REQUEST, "잘못된 WAV"));
        upload(event.getEventId(), 1).andExpect(status().isBadRequest());
        assertEquals(EventStatus.WAITING_AUDIO, reload(event).getStatus());
        assertNull(reload(event).getTranscript());
        assertNull(reload(event).getAudioHash());
        verifyNoInteractions(visitPushService);
    }

    @Test
    void modelFailureAllowsLaterRetryOfSameRecording() throws Exception {
        Event event = waitingEvent(1, 0, false);
        when(audioModelClient.process(any(MultipartFile.class)))
                .thenThrow(new ResponseStatusException(HttpStatus.SERVICE_UNAVAILABLE, "테스트용 모델 장애"))
                .thenReturn(delivery(List.of()));
        upload(event.getEventId(), 1).andExpect(status().isServiceUnavailable());
        assertNull(reload(event).getAudioHash());
        assertEquals(EventStatus.WAITING_AUDIO, reload(event).getStatus());
        upload(event.getEventId(), 1).andExpect(status().isOk());
        assertEquals("DELIVERY", reload(event).getPurpose());
        verify(visitPushService, times(1)).notifyVisit(any(Event.class));
    }

    @Test
    void packageStateFailureRollsBackAudioAndSkipsPush() throws Exception {
        Event event = waitingEvent(1, 1, false);
        doThrow(new IllegalStateException("테스트용 물품 상태 저장 실패"))
                .when(packageReceptionService).rememberCompletedEvent(any(Event.class), any(Instant.class));
        upload(event.getEventId(), 1).andExpect(status().isInternalServerError());
        Event saved = reload(event);
        assertEquals(EventStatus.WAITING_AUDIO, saved.getStatus());
        assertNull(saved.getTranscript());
        assertNull(saved.getPurpose());
        assertNull(saved.getAudioHash());
        assertNull(saved.getEndedAt());
        assertFalse(packageStateRepository.existsById(deviceId));
        verifyNoInteractions(visitPushService);
    }

    @Test
    void tooLargeModelTranscriptReturns503BeforeDatabaseWrite() throws Exception {
        Event event = waitingEvent(1, 0, false);
        when(audioModelClient.process(any(MultipartFile.class))).thenReturn(
                new AudioProcessResponse("가".repeat(21_846), "UNKNOWN", null, "요약", List.of()));
        upload(event.getEventId(), 1).andExpect(status().isServiceUnavailable());
        assertNull(reload(event).getTranscript());
        assertEquals(EventStatus.WAITING_AUDIO, reload(event).getStatus());
        verifyNoInteractions(visitPushService);
    }

    @Test
    void lateEndPreservesStoredVoiceResult() throws Exception {
        Event event = waitingEvent(1, 0, false);
        upload(event.getEventId(), 1).andExpect(status().isOk());
        Instant completedAt = reload(event).getEndedAt();
        String json = "{\"reason\":\"TIMEOUT\",\"endedAt\":\"" + Instant.now() + "\"}";
        mockMvc.perform(post("/api/v1/device/events/{eventId}/end", event.getEventId())
                        .contentType(MediaType.APPLICATION_JSON).content(json))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.action").value("END_SESSION"));
        assertEquals("DELIVERY", reload(event).getPurpose());
        assertEquals("VISITOR_ACCEPTED", reload(event).getEventType());
        assertEquals(completedAt, reload(event).getEndedAt());
        verify(visitPushService, times(1)).notifyVisit(any(Event.class));
    }

    @Test
    void bothModelFailuresCloseAsB2AndPushAfterCommitWhileReturning503() throws Exception {
        Event event = imageFailureEvent();
        when(audioModelClient.process(any(MultipartFile.class)))
                .thenThrow(new ResponseStatusException(HttpStatus.SERVICE_UNAVAILABLE, "음성 모델 장애"));
        doAnswer(invocation -> {
            assertFalse(TransactionSynchronizationManager.isActualTransactionActive());
            assertEquals(EventStatus.COMPLETED, reload(event).getStatus());
            assertEquals("이미지·음성 분석 실패", reload(event).getReason());
            return null;
        }).when(visitPushService).notifyVisit(any(Event.class));

        upload(event.getEventId(), 1)
                .andExpect(status().isServiceUnavailable())
                .andExpect(jsonPath("$.code").value("MODEL_SERVICE_UNAVAILABLE"));

        Event saved = reload(event);
        assertEquals(EventStatus.COMPLETED, saved.getStatus());
        assertEquals("VISITOR_TIMEOUT", saved.getEventType());
        assertEquals("기타·판단 불가", saved.getMainCategory());
        assertEquals("장애 안내", saved.getResponsePolicy());
        assertEquals("이미지 판단 실패", saved.getProcessingStatus());
        assertTrue(saved.getNeedsReview());
        assertNotNull(saved.getEndedAt());
        assertNull(saved.getPurpose());
        assertNull(saved.getTranscript());
        assertNull(saved.getSummary());
        assertNull(saved.getAudioHash());
        verify(visitPushService, times(1)).notifyVisit(any(Event.class));
    }

    @Test
    void invalidAudioAfterImageFailureDoesNotCloseReception() throws Exception {
        Event event = imageFailureEvent();
        when(audioModelClient.process(any(MultipartFile.class)))
                .thenThrow(new ResponseStatusException(HttpStatus.BAD_REQUEST, "WAV 형식 오류"));
        upload(event.getEventId(), 1).andExpect(status().isBadRequest());
        assertEquals(EventStatus.WAITING_AUDIO, reload(event).getStatus());
        assertNull(reload(event).getEndedAt());
        verifyNoInteractions(visitPushService);
    }

    @Test
    void noSpeechSuccessAfterImageFailureStillUsesVoiceClassification() throws Exception {
        Event event = imageFailureEvent();
        when(audioModelClient.process(any(MultipartFile.class))).thenReturn(
                new AudioProcessResponse("", "UNKNOWN", null, "", List.of("NO_SPEECH")));
        upload(event.getEventId(), 1).andExpect(status().isOk());
        Event saved = reload(event);
        assertEquals("VISITOR_ACCEPTED", saved.getEventType());
        assertEquals("UNKNOWN", saved.getPurpose());
        assertEquals("이미지 판단 실패", saved.getProcessingStatus());
        assertEquals("일반 접수", saved.getResponsePolicy());
        assertNotNull(saved.getAudioHash());
    }

    @Test
    void failedReanalysisPreservesPreviousSuccessfulAudioAfterA0() throws Exception {
        Event event = imageFailureEvent();
        upload(event.getEventId(), 1).andExpect(status().isOk());
        Event previous = reload(event);
        when(audioModelClient.process(any(MultipartFile.class)))
                .thenThrow(new ResponseStatusException(HttpStatus.SERVICE_UNAVAILABLE, "재분석 장애"));
        upload(event.getEventId(), 2).andExpect(status().isServiceUnavailable());
        Event saved = reload(event);
        assertEquals("DELIVERY", saved.getPurpose());
        assertEquals(previous.getAudioHash(), saved.getAudioHash());
        assertEquals(previous.getEndedAt(), saved.getEndedAt());
        assertEquals(previous.getReason(), saved.getReason());
        verify(visitPushService, times(1)).notifyVisit(any(Event.class));
    }

    @Test
    void audioAfterBothFailureCompletionReturns409WithoutAnotherModelOrPush() throws Exception {
        Event event = imageFailureEvent();
        when(audioModelClient.process(any(MultipartFile.class)))
                .thenThrow(new ResponseStatusException(HttpStatus.SERVICE_UNAVAILABLE, "음성 모델 장애"));
        upload(event.getEventId(), 1).andExpect(status().isServiceUnavailable());
        Instant ended = reload(event).getEndedAt();
        upload(event.getEventId(), 1).andExpect(status().isConflict());
        assertEquals(ended, reload(event).getEndedAt());
        verify(audioModelClient, times(1)).process(any(MultipartFile.class));
        verify(visitPushService, times(1)).notifyVisit(any(Event.class));
    }

    @Test
    void lateEndAfterBothFailuresPreservesFailureReason() throws Exception {
        Event event = imageFailureEvent();
        when(audioModelClient.process(any(MultipartFile.class)))
                .thenThrow(new ResponseStatusException(HttpStatus.SERVICE_UNAVAILABLE, "음성 모델 장애"));
        upload(event.getEventId(), 1).andExpect(status().isServiceUnavailable());
        Instant ended = reload(event).getEndedAt();
        String json = "{\"reason\":\"TIMEOUT\",\"endedAt\":\"" + Instant.now() + "\"}";
        mockMvc.perform(post("/api/v1/device/events/{eventId}/end", event.getEventId())
                        .contentType(MediaType.APPLICATION_JSON).content(json))
                .andExpect(status().isOk()).andExpect(jsonPath("$.action").value("END_SESSION"));
        assertEquals("이미지·음성 분석 실패", reload(event).getReason());
        assertEquals(ended, reload(event).getEndedAt());
        verify(visitPushService, times(1)).notifyVisit(any(Event.class));
    }

    @Test
    void databaseFailureDuringBothFailureCompletionRollsBackAndSkipsPush() throws Exception {
        Event event = imageFailureEvent();
        when(audioModelClient.process(any(MultipartFile.class)))
                .thenThrow(new ResponseStatusException(HttpStatus.SERVICE_UNAVAILABLE, "음성 모델 장애"));
        doThrow(new IllegalStateException("종료 저장 중 물품 처리 장애"))
                .when(packageReceptionService).rememberCompletedEvent(any(Event.class), any(Instant.class));
        upload(event.getEventId(), 1).andExpect(status().isInternalServerError());
        Event saved = reload(event);
        assertEquals(EventStatus.WAITING_AUDIO, saved.getStatus());
        assertNull(saved.getEndedAt());
        assertNull(saved.getEventType());
        assertNull(saved.getTranscript());
        verifyNoInteractions(visitPushService);
    }

    private Event imageFailureEvent() {
        Event event = new Event(deviceId, "BUTTON", EventStatus.WAITING_AUDIO, photoAt);
        event.recordImageReception(photoAt, null);
        event.applyImageClassification(imageClassificationService.modelUnavailable(), photoAt);
        return eventRepository.saveAndFlush(event);
    }

    private Event waitingEvent(int people, int packages, boolean lowVisibility) {
        List<VisionResponse.Detection> detections = new ArrayList<>();
        for (int i = 0; i < people; i++) {
            detections.add(new VisionResponse.Detection("person", 0.9));
        }
        for (int i = 0; i < packages; i++) {
            detections.add(new VisionResponse.Detection("package", 0.9));
        }
        ImageClassificationResult classification = imageClassificationService.classify("BUTTON",
                new VisionResponse(detections, lowVisibility ? List.of("LOW_VISIBILITY") : List.of()));
        Event event = new Event(deviceId, "BUTTON", EventStatus.WAITING_AUDIO, photoAt);
        event.recordImageReception(photoAt, packages);
        event.applyImageClassification(classification, photoAt);
        event.attachSnapshot("existing.jpg");
        return eventRepository.saveAndFlush(event);
    }

    private Event reload(Event event) {
        return eventRepository.findById(event.getEventId()).orElseThrow();
    }

    private AudioProcessResponse delivery(List<String> flags) {
        return new AudioProcessResponse("택배 왔습니다. 문 앞에 놓고 갈게요.",
                "DELIVERY", "PARCEL", "택배 문 앞 보관", flags);
    }

    private ResultActions upload(Long eventId, int variant) throws Exception {
        return mockMvc.perform(multipart("/api/v1/device/events/{eventId}/audio", eventId)
                .file(audio(variant, "delivery.wav")));
    }

    private MockMultipartFile audio(int variant, String filename) {
        ByteBuffer wav = ByteBuffer.allocate(44 + 320).order(ByteOrder.LITTLE_ENDIAN);
        wav.put("RIFF".getBytes(StandardCharsets.US_ASCII)).putInt(36 + 320);
        wav.put("WAVEfmt ".getBytes(StandardCharsets.US_ASCII)).putInt(16);
        wav.putShort((short) 1).putShort((short) 1).putInt(16_000).putInt(32_000);
        wav.putShort((short) 2).putShort((short) 16);
        wav.put("data".getBytes(StandardCharsets.US_ASCII)).putInt(320);
        wav.putShort((short) variant);
        return new MockMultipartFile("audio", filename, "audio/wav", wav.array());
    }
}
