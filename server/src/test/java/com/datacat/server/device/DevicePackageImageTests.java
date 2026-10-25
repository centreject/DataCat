package com.datacat.server.device;

import com.datacat.server.classification.ImageClassificationResult;
import com.datacat.server.event.Event;
import com.datacat.server.event.EventExceptionHandler;
import com.datacat.server.event.EventRepository;
import com.datacat.server.event.EventStatus;
import com.datacat.server.model.AudioProcessResponse;
import com.datacat.server.model.VisionModelClient;
import com.datacat.server.model.VisionResponse;
import com.datacat.server.push.VisitPushService;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.context.bean.override.mockito.MockitoSpyBean;
import org.springframework.test.util.ReflectionTestUtils;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;
import org.springframework.transaction.support.TransactionSynchronizationManager;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.server.ResponseStatusException;
import tools.jackson.databind.ObjectMapper;

import javax.imageio.ImageIO;
import java.awt.image.BufferedImage;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.multipart;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest
@ActiveProfiles("test")
class DevicePackageImageTests {
    private static final Path PHOTOS = temporaryPhotoDirectory();
    @DynamicPropertySource static void storage(DynamicPropertyRegistry registry) {
        registry.add("datacat.storage.snapshot-dir", PHOTOS::toString);
    }

    @Autowired private DeviceEventService service;
    @Autowired private EventRepository events;
    @Autowired private DevicePackageStateRepository states;
    @Autowired private DeviceSessionAudioService audioService;
    @Autowired private ObjectMapper mapper;
    @MockitoBean private VisionModelClient visionClient;
    @MockitoBean private VisitPushService push;
    @MockitoSpyBean private PackageReceptionService packages;

    private MockMvc mvc;
    private String deviceId;
    private VisionResponse scenario;

    @BeforeEach void setUp() {
        deviceId = "image-presence-" + UUID.randomUUID();
        mvc = MockMvcBuilders.standaloneSetup(new DeviceEventController(service))
                .setControllerAdvice(new EventExceptionHandler())
                .defaultResponseCharacterEncoding(StandardCharsets.UTF_8).build();
        when(visionClient.detect(any(MultipartFile.class))).thenAnswer(invocation -> {
            assertFalse(TransactionSynchronizationManager.isActualTransactionActive(), "모델 호출 중 DB 트랜잭션");
            return scenario;
        });
        doAnswer(invocation -> {
            assertFalse(TransactionSynchronizationManager.isActualTransactionActive(), "커밋 전 푸시 호출");
            Event saved = invocation.getArgument(0);
            assertTrue(events.existsById(saved.getEventId()));
            return null;
        }).when(push).notifyVisit(any(Event.class));
    }

    @AfterEach void removeOnlyThisClassPhotos() throws IOException {
        try (var files = Files.list(PHOTOS)) {
            for (Path file : files.toList()) Files.deleteIfExists(file);
        }
    }

    @Test void repeatedPackageOutsideMergeWindowKeepsEventAndDiscardsUnusedPhoto() throws Exception {
        long first = upload(vision(0, 1), "TOF", 201);
        Event original = events.findById(first).orElseThrow();
        Path originalPhoto = PHOTOS.resolve(original.getSnapshotPath());
        Instant firstSeen = state().getFirstSeenAt();
        expirePhotoWindow(first);
        long repeated = upload(vision(0, 1), "TOF", 200);
        assertEquals(first, repeated);
        assertEquals(1, eventCount());
        assertEquals(1, photoCount());
        assertTrue(Files.exists(originalPhoto));
        assertEquals(original.getSnapshotPath(), events.findById(first).orElseThrow().getSnapshotPath());
        assertEquals(firstSeen, state().getFirstSeenAt());
        assertFalse(state().getLastSeenAt().isBefore(firstSeen));
        verify(push, times(1)).notifyVisit(any(Event.class));
    }

    @Test void countChangesDoNotCreateAnotherArrival() throws Exception {
        long first = upload(vision(0, 1), "TOF", 201);
        assertEquals(first, upload(vision(0, 3), "TOF", 200));
        assertEquals(first, upload(vision(0, 1), "TOF", 200));
        assertEquals(1, eventCount());
        assertEquals(1, photoCount());
        verify(push, times(1)).notifyVisit(any(Event.class));
    }

    @Test void oneEmptyPhotoThenPackageKeepsPresenceAndResetsMisses() throws Exception {
        long first = upload(vision(0, 1), "TOF", 201);
        upload(vision(0, 0), "TOF", 200);
        assertEquals(1, state().getMissCount());
        assertEquals(first, upload(vision(0, 1), "TOF", 200));
        assertEquals(0, state().getMissCount());
        assertTrue(state().getPackagePresent());
        assertEquals(1, eventCount());
        verify(push, times(1)).notifyVisit(any(Event.class));
    }

    @Test void twoEmptyPhotosClearOnlyStateAndNextPackageCreatesNewArrival() throws Exception {
        long first = upload(vision(0, 1), "TOF", 201);
        upload(vision(0, 0), "TOF", 200);
        assertTrue(states.existsById(deviceId));
        upload(vision(0, 0), "TOF", 200);
        assertFalse(states.existsById(deviceId));
        assertTrue(events.existsById(first));
        long next = upload(vision(0, 1), "TOF", 201);
        assertNotEquals(first, next);
        assertEquals(next, state().getPackageEventId());
        assertEquals(2, eventCount());
        verify(push, times(2)).notifyVisit(any(Event.class));
    }

    @Test void coveredPhotoDoesNotCountAsMissingOrClearState() throws Exception {
        upload(vision(0, 1), "TOF", 201);
        upload(vision(0, 0), "TOF", 200);
        VisionResponse covered = new VisionResponse(List.of(), List.of("LOW_VISIBILITY"));
        upload(covered, "TOF", 200);
        upload(covered, "TOF", 200);
        assertEquals(1, state().getMissCount());
        assertTrue(state().getPackagePresent());
        verify(push, times(1)).notifyVisit(any(Event.class));
    }

    @Test void personAfterCompletedPackageStartsNewSessionWithoutClearingPresence() throws Exception {
        long first = upload(vision(0, 1), "TOF", 201);
        long person = upload(vision(1, 0), "TOF", 201);
        assertNotEquals(first, person);
        assertEquals(EventStatus.COMPLETED, events.findById(first).orElseThrow().getStatus());
        assertEquals(EventStatus.WAITING_AUDIO, events.findById(person).orElseThrow().getStatus());
        assertEquals(first, state().getPackageEventId());
        assertEquals(2, photoCount());
        verify(push, times(2)).notifyVisit(any(Event.class));
    }

    @Test void buttonAfterCompletedPackageStartsNewSessionEvenWithoutPerson() throws Exception {
        long first = upload(vision(0, 1), "TOF", 201);
        long button = upload(vision(0, 0), "BUTTON", 201);
        assertNotEquals(first, button);
        assertEquals(EventStatus.WAITING_AUDIO, events.findById(button).orElseThrow().getStatus());
        assertTrue(state().getPackagePresent());
        assertEquals(0, state().getMissCount());
    }

    @Test void packagePhotoDuringActiveReceptionWaitsForAudioAndIsRememberedOnEnd() throws Exception {
        long person = upload(vision(1, 0), "TOF", 201);
        assertEquals(person, upload(vision(0, 2), "TOF", 200));
        Event waiting = events.findById(person).orElseThrow();
        assertEquals(EventStatus.WAITING_AUDIO, waiting.getStatus());
        assertTrue(waiting.getPackageSeen());
        assertEquals("A1", waiting.getImageRuleId());
        assertFalse(states.existsById(deviceId));
        verify(push, times(1)).notifyVisit(any(Event.class));
        end(person);
        assertEquals(person, state().getPackageEventId());
        expirePhotoWindow(person);
        assertEquals(person, upload(vision(0, 1), "TOF", 200));
        verify(push, times(2)).notifyVisit(any(Event.class));
    }

    @Test void newSessionCompletionUpdatesReferenceAndLaterPackageDoesNotPush() throws Exception {
        long old = upload(vision(0, 1), "TOF", 201);
        Instant firstSeen = state().getFirstSeenAt();
        long next = upload(vision(1, 1), "BUTTON", 201);
        end(next);
        assertEquals(next, state().getPackageEventId());
        assertEquals(firstSeen, state().getFirstSeenAt());
        assertTrue(events.existsById(old));
        assertEquals(next, upload(vision(0, 3), "TOF", 200));
        assertEquals(2, eventCount());
        verify(push, times(3)).notifyVisit(any(Event.class));
    }

    @Test void packageAfterVoiceCompletionPreservesVoiceResultAndDoesNotPushAgain() throws Exception {
        long first = upload(vision(1, 1), "BUTTON", 201);
        audioService.saveAnalysis(first, "a".repeat(64),
                new AudioProcessResponse("택배입니다", "DELIVERY", "PARCEL", "택배", List.of()), Instant.now());
        assertEquals(first, upload(vision(0, 1), "TOF", 200));
        Event completed = events.findById(first).orElseThrow();
        assertEquals(EventStatus.COMPLETED, completed.getStatus());
        assertEquals("DELIVERY", completed.getPurpose());
        assertEquals("택배입니다", completed.getTranscript());
        verify(push, times(1)).notifyVisit(any(Event.class));
    }

    @Test void modelFailureDoesNotClearOrIncrementExistingPresenceMisses() throws Exception {
        upload(vision(0, 1), "TOF", 201);
        upload(vision(0, 0), "TOF", 200);
        when(visionClient.detect(any())).thenThrow(
                new ResponseStatusException(HttpStatus.SERVICE_UNAVAILABLE, "테스트 모델 장애"));
        MvcResult response = perform("TOF", 201);
        assertEquals("WAITING_AUDIO", mapper.readTree(response.getResponse().getContentAsString()).get("status").asText());
        assertEquals(1, state().getMissCount());
        assertTrue(state().getPackagePresent());
    }

    @Test void packageFailureRollsBackNewEventAndStateAndCleansNewPhoto() throws Exception {
        doAnswer(invocation -> {
            invocation.callRealMethod();
            throw new IllegalStateException("물품 상태 저장 후 장애");
        }).when(packages).receive(any(DeviceEventMetadata.class), any(ImageClassificationResult.class),
                anyString(), anyString(), any(Instant.class));
        scenario = vision(0, 1);
        perform("TOF", 500);
        assertEquals(0, eventCount());
        assertFalse(states.existsById(deviceId));
        assertEquals(0, photoCount());
        verifyNoInteractions(push);
    }

    @Test void missingStateFailureRollsBackPhotoReplacementAndStateDeletion() throws Exception {
        long first = upload(vision(0, 1), "TOF", 201);
        upload(vision(0, 0), "TOF", 200);
        String snapshot = events.findById(first).orElseThrow().getSnapshotPath();
        doAnswer(invocation -> {
            invocation.callRealMethod();
            throw new IllegalStateException("상태 삭제 후 장애");
        }).when(packages).observeMissing(deviceId);
        scenario = vision(0, 0);
        perform("TOF", 500);
        assertEquals(1, state().getMissCount());
        assertEquals(snapshot, events.findById(first).orElseThrow().getSnapshotPath());
        assertTrue(Files.exists(PHOTOS.resolve(snapshot)));
        assertEquals(1, photoCount());
        verify(push, times(1)).notifyVisit(any(Event.class));
    }

    private long upload(VisionResponse response, String trigger, int expected) throws Exception {
        scenario = response;
        return mapper.readTree(perform(trigger, expected).getResponse().getContentAsString()).get("eventId").asLong();
    }
    private MvcResult perform(String trigger, int expected) throws Exception {
        String metadata = "{\"deviceId\":\"%s\",\"triggerType\":\"%s\",\"distanceMm\":1850,\"capturedAt\":\"%s\"}"
                .formatted(deviceId, trigger, Instant.now());
        return mvc.perform(multipart("/api/v1/device/events")
                        .file(new MockMultipartFile("metadata", "metadata.json", "application/json", metadata.getBytes(StandardCharsets.UTF_8)))
                        .file(new MockMultipartFile("image", "photo.jpg", "image/jpeg", jpeg())))
                .andExpect(status().is(expected)).andReturn();
    }
    private void end(long id) throws Exception {
        String json = "{\"reason\":\"TIMEOUT\",\"endedAt\":\"" + Instant.now() + "\"}";
        mvc.perform(post("/api/v1/device/events/{eventId}/end", id)
                        .contentType(MediaType.APPLICATION_JSON).content(json))
                .andExpect(status().isOk()).andExpect(jsonPath("$.action").value("END_SESSION"));
    }
    private DevicePackageState state() { return states.findById(deviceId).orElseThrow(); }
    private long eventCount() { return events.findAll().stream().filter(e -> deviceId.equals(e.getDeviceId())).count(); }
    private long photoCount() throws IOException {
        try (var files = Files.list(PHOTOS)) { return files.count(); }
    }
    private void expirePhotoWindow(long id) {
        Event event = events.findById(id).orElseThrow();
        ReflectionTestUtils.setField(event, "lastImageReceivedAt", Instant.now().minusSeconds(61));
        events.saveAndFlush(event);
    }
    private VisionResponse vision(int people, int count) {
        List<VisionResponse.Detection> detections = new ArrayList<>();
        for (int i = 0; i < people; i++) detections.add(new VisionResponse.Detection("person", .95));
        for (int i = 0; i < count; i++) detections.add(new VisionResponse.Detection("package", .95));
        return new VisionResponse(detections, List.of());
    }
    private byte[] jpeg() throws IOException {
        BufferedImage picture = new BufferedImage(32, 24, BufferedImage.TYPE_INT_RGB);
        ByteArrayOutputStream output = new ByteArrayOutputStream();
        ImageIO.write(picture, "jpeg", output);
        return output.toByteArray();
    }
    private static Path temporaryPhotoDirectory() {
        try { return Files.createTempDirectory("datacat-package-images-"); }
        catch (IOException e) { throw new IllegalStateException(e); }
    }
}
