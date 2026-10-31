package com.datacat.server.event;

import org.springframework.data.jpa.repository.JpaRepository;

import java.time.Instant;
import java.util.Optional;

public interface EventRepository extends JpaRepository<Event, Long> {

    Optional<Event>
    findFirstByDeviceIdAndLastImageReceivedAtGreaterThanEqualOrderByLastImageReceivedAtDescEventIdDesc(
            String deviceId,
            Instant cutoff
    );
}