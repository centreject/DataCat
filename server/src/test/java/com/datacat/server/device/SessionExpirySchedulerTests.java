package com.datacat.server.device;

import com.datacat.server.event.Event;
import com.datacat.server.event.EventRepository;
import com.datacat.server.event.EventStatus;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.annotation.DirtiesContext;
import org.springframework.test.context.ActiveProfiles;

import java.time.Instant;

import static org.junit.jupiter.api.Assertions.*;

@SpringBootTest(properties = {
        "spring.datasource.url=jdbc:h2:mem:datacat_scheduler;MODE=MySQL;DB_CLOSE_DELAY=-1",
        "datacat.session.expiry-enabled=true",
        "datacat.session.idle-timeout-ms=1000",
        "datacat.session.expiry-check-ms=50"
})
@ActiveProfiles("test")
@DirtiesContext(classMode = DirtiesContext.ClassMode.AFTER_CLASS)
class SessionExpirySchedulerTests {
    @Autowired EventRepository events;

    @Test
    void schedulerCompletesAbandonedVisitWithoutPiEndRequest() throws Exception {
        Event event = events.saveAndFlush(new Event("scheduler-device", "TOF",
                EventStatus.WAITING_AUDIO, Instant.now().minusSeconds(30)));
        long deadline = System.nanoTime() + 5_000_000_000L;
        Event saved;
        do {
            saved = events.findById(event.getEventId()).orElseThrow();
            if (saved.getStatus() == EventStatus.COMPLETED) break;
            Thread.sleep(20);
        } while (System.nanoTime() < deadline);
        assertEquals(EventStatus.COMPLETED, saved.getStatus());
        assertTrue(saved.getNeedsReview());
        assertEquals("후속 요청 없이 세션 대기 시간 초과", saved.getReason());
    }
}
