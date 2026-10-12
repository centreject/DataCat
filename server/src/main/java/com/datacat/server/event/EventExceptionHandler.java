package com.datacat.server.event;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.method.annotation.MethodArgumentTypeMismatchException;
import org.springframework.web.server.ResponseStatusException;

@RestControllerAdvice(assignableTypes = EventController.class)
public class EventExceptionHandler {

    private static final Logger log =
            LoggerFactory.getLogger(EventExceptionHandler.class);

    @ExceptionHandler(ResponseStatusException.class)
    public ResponseEntity<EventErrorResponse> handleResponseStatus(
            ResponseStatusException exception
    ) {
        String code = "INVALID_REQUEST";

        if (exception.getStatusCode().value() == 404) {
            code = "NOT_FOUND";
        }

        EventErrorResponse response = new EventErrorResponse(
                code,
                exception.getReason()
        );

        return ResponseEntity
                .status(exception.getStatusCode())
                .body(response);
    }

    @ExceptionHandler(MethodArgumentTypeMismatchException.class)
    public ResponseEntity<EventErrorResponse> handleTypeMismatch(
            MethodArgumentTypeMismatchException exception
    ) {
        EventErrorResponse response = new EventErrorResponse(
                "INVALID_REQUEST",
                exception.getName() + " 값은 정수로 입력해야 합니다."
        );

        return ResponseEntity
                .status(HttpStatus.BAD_REQUEST)
                .body(response);
    }

    @ExceptionHandler(Exception.class)
    public ResponseEntity<EventErrorResponse> handleUnexpected(
            Exception exception
    ) {
        log.error("이벤트 조회 중 예상하지 못한 오류가 발생했습니다.", exception);

        EventErrorResponse response = new EventErrorResponse(
                "INTERNAL_SERVER_ERROR",
                "서버 처리 중 오류가 발생했습니다."
        );

        return ResponseEntity
                .status(HttpStatus.INTERNAL_SERVER_ERROR)
                .body(response);
    }
}