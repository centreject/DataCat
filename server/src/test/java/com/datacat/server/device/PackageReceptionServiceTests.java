package com.datacat.server.device;

import com.datacat.server.classification.ImageClassificationResult;
import com.datacat.server.classification.ImageClassificationService;
import com.datacat.server.event.EventRepository;
import com.datacat.server.model.VisionResponse;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;
import java.time.ZoneOffset;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

@SpringBootTest
@ActiveProfiles("test")
@Transactional
class PackageReceptionServiceTests {

    @Autowired
    private PackageReceptionService service;

    @Autowired
    private ImageClassificationService classificationService;

    @Autowired
    private EventRepository eventRepository;

    @Autowired
    private DevicePackageStateRepository packageStateRepository;

    private String deviceId;

    @BeforeEach
    void setUp() {
        deviceId = "package-db-test-"
                + UUID.randomUUID();
    }

    @Test
    void samePackageAfterThirtySecondsReusesEvent() {
        Instant firstTime = Instant.parse("2026-10-21T06:00:00Z");
        Instant secondTime = firstTime.plusSeconds(61);
        long countBefore = eventRepository.count();

        PackageReceptionService.ReceptionResult first =
                receive(1, "first.jpg", firstTime);

        PackageReceptionService.ReceptionResult second =
                receive(1, "unused.jpg", secondTime);

        DevicePackageState state = packageStateRepository
                .findById(deviceId)
                .orElseThrow();

        assertTrue(first.created());
        assertFalse(second.created());

        assertEquals(
                first.event().getEventId(),
                second.event().getEventId()
        );

        assertEquals(countBefore + 1, eventRepository.count());
        assertEquals("first.jpg", second.event().getSnapshotPath());
        assertEquals(1, state.getPackageCount());
        assertEquals(firstTime, state.getFirstSeenAt());
        assertEquals(secondTime, state.getLastSeenAt());
    }

    @Test
    void additionalPackageCreatesNewEvent() {
        Instant firstTime = Instant.parse("2026-10-21T06:00:00Z");
        Instant secondTime = firstTime.plusSeconds(61);
        long countBefore = eventRepository.count();

        PackageReceptionService.ReceptionResult first =
                receive(1, "first.jpg", firstTime);

        PackageReceptionService.ReceptionResult second =
                receive(2, "second.jpg", secondTime);

        DevicePackageState state = packageStateRepository
                .findById(deviceId)
                .orElseThrow();

        assertTrue(second.created());

        assertNotEquals(
                first.event().getEventId(),
                second.event().getEventId()
        );

        assertEquals(countBefore + 2, eventRepository.count());
        assertEquals("물품 추가 (1개 → 2개)", second.event().getReason());
        assertEquals(2, state.getPackageCount());

        assertEquals(
                second.event().getEventId(),
                state.getPackageEventId()
        );

        assertEquals(firstTime, state.getFirstSeenAt());
        assertEquals(secondTime, state.getLastSeenAt());
    }

    @Test
    void fewerDetectionsDoNotCauseAnotherArrival() {
        Instant firstTime = Instant.parse("2026-10-21T06:00:00Z");
        long countBefore = eventRepository.count();

        PackageReceptionService.ReceptionResult first =
                receive(2, "first.jpg", firstTime);

        PackageReceptionService.ReceptionResult fewer =
                receive(1, "fewer.jpg", firstTime.plusSeconds(61));

        PackageReceptionService.ReceptionResult sameAgain =
                receive(2, "same-again.jpg", firstTime.plusSeconds(122));

        DevicePackageState state = packageStateRepository
                .findById(deviceId)
                .orElseThrow();

        assertFalse(fewer.created());
        assertFalse(sameAgain.created());

        assertEquals(
                first.event().getEventId(),
                sameAgain.event().getEventId()
        );

        assertEquals(2, state.getPackageCount());
        assertEquals(countBefore + 1, eventRepository.count());
    }

    @Test
    void clearingStateKeepsVisitHistory() {
        Instant firstTime = Instant.parse("2026-10-21T06:00:00Z");

        PackageReceptionService.ReceptionResult first =
                receive(1, "first.jpg", firstTime);

        service.clearForDevice(deviceId);

        assertFalse(packageStateRepository.existsById(deviceId));

        assertTrue(
                eventRepository.existsById(
                        first.event().getEventId()
                )
        );
    }

    private PackageReceptionService.ReceptionResult receive(
            int packageCount,
            String snapshotFilename,
            Instant receivedAt
    ) {
        List<VisionResponse.Detection> detections =
                new ArrayList<>();

        for (int i = 0; i < packageCount; i++) {
            detections.add(new VisionResponse.Detection(
                    "package",
                    0.95
            ));
        }

        VisionResponse vision = new VisionResponse(
                detections,
                List.of()
        );

        ImageClassificationResult classification =
                classificationService.classify(
                        "TOF",
                        vision
                );

        DeviceEventMetadata metadata = new DeviceEventMetadata(
                deviceId,
                "TOF",
                1850,
                receivedAt.atOffset(ZoneOffset.UTC)
        );

        return service.receive(
                metadata,
                classification,
                snapshotFilename,
                "{}",
                receivedAt
        );
    }
}