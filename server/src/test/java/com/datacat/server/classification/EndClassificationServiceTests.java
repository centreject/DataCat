package com.datacat.server.classification;

import org.junit.jupiter.api.Test;
import org.springframework.http.HttpStatus;
import org.springframework.web.server.ResponseStatusException;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

class EndClassificationServiceTests {

    private final EndClassificationService service =
            new EndClassificationService();

    @Test
    void visitorLeftWithPackageUsesB1() {
        EndClassificationResult result =
                service.classify("VISITOR_LEFT", 1);

        assertEquals("UNATTENDED_DELIVERY", result.eventType());
        assertEquals("물품만 있음", result.mainCategory());
        assertEquals("무응답", result.responsePolicy());
        assertEquals("무응답", result.processingStatus());
        assertEquals("안내 전 이탈", result.reason());
    }

    @Test
    void timeoutWithPackageAlsoUsesB1() {
        EndClassificationResult result =
                service.classify("TIMEOUT", 2);

        assertEquals("UNATTENDED_DELIVERY", result.eventType());
        assertEquals("물품만 있음", result.mainCategory());
        assertEquals("발화 없이 시간 초과", result.reason());
    }

    @Test
    void visitorLeftWithoutPackageUsesB2() {
        EndClassificationResult result =
                service.classify("VISITOR_LEFT", 0);

        assertEquals("VISITOR_TIMEOUT", result.eventType());
        assertEquals("기타·판단 불가", result.mainCategory());
        assertEquals("안내 전 이탈", result.reason());
    }

    @Test
    void timeoutWithoutPackageUsesB2() {
        EndClassificationResult result =
                service.classify("TIMEOUT", 0);

        assertEquals("VISITOR_TIMEOUT", result.eventType());
        assertEquals("기타·판단 불가", result.mainCategory());
        assertEquals("무응답", result.responsePolicy());
        assertEquals("무응답", result.processingStatus());
        assertEquals("발화 없이 시간 초과", result.reason());
    }

    @Test
    void missingEndReasonIsRejected() {
        ResponseStatusException exception = assertThrows(
                ResponseStatusException.class,
                () -> service.classify(null, 0)
        );

        assertEquals(HttpStatus.BAD_REQUEST, exception.getStatusCode());
    }

    @Test
    void reservedEndReasonIsRejected() {
        ResponseStatusException exception = assertThrows(
                ResponseStatusException.class,
                () -> service.classify("DEVICE_CANCELLED", 0)
        );

        assertEquals(HttpStatus.BAD_REQUEST, exception.getStatusCode());
    }
}