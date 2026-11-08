package com.datacat.server.event;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.domain.Pageable;
import org.springframework.data.repository.query.Param;

import java.time.Instant;
import java.util.Optional;
import java.util.List;

public interface EventRepository extends JpaRepository<Event, Long> {

    @Query("""
            select e from Event e where e.status = :status
            and coalesce(e.lastSessionActivityAt, e.lastImageReceivedAt, e.occurredAt) <= :cutoff
            order by e.eventId
            """)
    List<Event> findInactiveSessions(@Param("status") EventStatus status,
                                   @Param("cutoff") Instant cutoff, Pageable pageable);

    Optional<Event>
    findFirstByDeviceIdAndLastImageReceivedAtGreaterThanEqualOrderByLastImageReceivedAtDescEventIdDesc(
            String deviceId,
            Instant cutoff
    );
}
