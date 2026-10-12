package com.datacat.server.event;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.CommandLineRunner;
import org.springframework.context.annotation.Profile;
import org.springframework.stereotype.Component;

import java.time.Instant;
import java.util.List;

@Component
@Profile("dev")
public class EventSampleData implements CommandLineRunner {

    private static final Logger log =
            LoggerFactory.getLogger(EventSampleData.class);

    private final EventRepository eventRepository;

    public EventSampleData(EventRepository eventRepository) {
        this.eventRepository = eventRepository;
    }

    @Override
    public void run(String... args) {
        if (eventRepository.count() > 0) {
            log.info("이벤트 데이터가 이미 있어 샘플 생성을 건너뜁니다.");
            return;
        }

        List<Event> samples = List.of(
                new Event(
                        "sample-door-01",
                        "TOF",
                        EventStatus.WAITING_AUDIO,
                        Instant.parse("2026-10-05T06:00:00Z")
                ),
                new Event(
                        "sample-door-01",
                        "BUTTON",
                        EventStatus.WAITING_AUDIO,
                        Instant.parse("2026-10-05T06:05:00Z")
                ),
                new Event(
                        "sample-door-02",
                        "TOF",
                        EventStatus.WAITING_AUDIO,
                        Instant.parse("2026-10-05T06:10:00Z")
                )
        );

        eventRepository.saveAll(samples);

        log.info("개발용 샘플 이벤트 {}건을 저장했습니다.", samples.size());
    }
}