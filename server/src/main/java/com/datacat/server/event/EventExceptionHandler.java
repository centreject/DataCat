package com.datacat.server.event;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.web.HttpMediaTypeNotSupportedException;
import org.springframework.web.HttpRequestMethodNotSupportedException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.method.annotation.MethodArgumentTypeMismatchException;
import org.springframework.web.multipart.MaxUploadSizeExceededException;
import org.springframework.web.multipart.support.MissingServletRequestPartException;
import org.springframework.web.server.ResponseStatusException;
import org.springframework.web.servlet.NoHandlerFoundException;
import org.springframework.web.servlet.resource.NoResourceFoundException;

@RestControllerAdvice
public class EventExceptionHandler {

    private static final Logger log =
            LoggerFactory.getLogger(EventExceptionHandler.class);

    @ExceptionHandler(ResponseStatusException.class)
    public ResponseEntity<EventErrorResponse> handleResponseStatus(
            ResponseStatusException exception
    ) {
        int status = exception.getStatusCode().value();

        String code = switch (status) {
            case 400 -> "INVALID_REQUEST";
            case 404 -> "NOT_FOUND";
            case 409 -> "EVENT_STATE_CONFLICT";
            case 503 -> "MODEL_SERVICE_UNAVAILABLE";
            default -> "INTERNAL_SERVER_ERROR";
        };

        if (status >= 500) {
            log.error("서버 요청 처리에 실패했습니다.", exception);
        }

        String message = exception.getReason();

        if (message == null) {
            message = "요청을 처리할 수 없습니다.";
        }

        return ResponseEntity
                .status(exception.getStatusCode())
                .body(new EventErrorResponse(code, message));
    }

    @ExceptionHandler(MethodArgumentTypeMismatchException.class)
    public ResponseEntity<EventErrorResponse> handleTypeMismatch(
            MethodArgumentTypeMismatchException exception
    ) {
        return error(
                HttpStatus.BAD_REQUEST,
                "INVALID_REQUEST",
                exception.getName() + " 값은 정수로 입력해야 합니다."
        );
    }

    @ExceptionHandler(MissingServletRequestPartException.class)
    public ResponseEntity<EventErrorResponse> handleMissingPart(
            MissingServletRequestPartException exception
    ) {
        return error(
                HttpStatus.BAD_REQUEST,
                "INVALID_REQUEST",
                exception.getRequestPartName() + " 파트가 필요합니다."
        );
    }

    @ExceptionHandler(HttpMessageNotReadableException.class)
    public ResponseEntity<EventErrorResponse> handleInvalidJson(
            HttpMessageNotReadableException exception
    ) {
        return error(
                HttpStatus.BAD_REQUEST,
                "INVALID_REQUEST",
                "JSON 형식 또는 필드 값이 올바르지 않습니다."
        );
    }

    @ExceptionHandler(MaxUploadSizeExceededException.class)
    public ResponseEntity<EventErrorResponse> handleUploadSize(
            MaxUploadSizeExceededException exception
    ) {
        return error(
                HttpStatus.BAD_REQUEST,
                "INVALID_REQUEST",
                "파일 또는 전체 업로드 요청이 크기 제한을 초과했습니다."
        );
    }

    @ExceptionHandler(HttpMediaTypeNotSupportedException.class)
    public ResponseEntity<EventErrorResponse> handleContentType(
            HttpMediaTypeNotSupportedException exception
    ) {
        return error(
                HttpStatus.UNSUPPORTED_MEDIA_TYPE,
                "UNSUPPORTED_MEDIA_TYPE",
                "요청 또는 multipart 파트의 Content-Type을 확인해 주세요."
        );
    }

    @ExceptionHandler(HttpRequestMethodNotSupportedException.class)
    public ResponseEntity<EventErrorResponse> handleMethod(
            HttpRequestMethodNotSupportedException exception
    ) {
        HttpHeaders headers = new HttpHeaders();

        if (exception.getSupportedHttpMethods() != null) {
            headers.setAllow(exception.getSupportedHttpMethods());
        }

        return ResponseEntity
                .status(HttpStatus.METHOD_NOT_ALLOWED)
                .headers(headers)
                .body(new EventErrorResponse(
                        "METHOD_NOT_ALLOWED",
                        "허용되지 않는 HTTP 요청 메서드입니다."
                ));
    }

    @ExceptionHandler({
            NoResourceFoundException.class,
            NoHandlerFoundException.class
    })
    public ResponseEntity<EventErrorResponse> handleUnknownPath(
            Exception exception
    ) {
        return error(
                HttpStatus.NOT_FOUND,
                "NOT_FOUND",
                "요청한 경로를 찾을 수 없습니다."
        );
    }

    @ExceptionHandler(Exception.class)
    public ResponseEntity<EventErrorResponse> handleUnexpected(
            Exception exception
    ) {
        log.error("예상하지 못한 서버 오류가 발생했습니다.", exception);

        return error(
                HttpStatus.INTERNAL_SERVER_ERROR,
                "INTERNAL_SERVER_ERROR",
                "서버 처리 중 오류가 발생했습니다."
        );
    }

    private ResponseEntity<EventErrorResponse> error(
            HttpStatus status,
            String code,
            String message
    ) {
        return ResponseEntity
                .status(status)
                .body(new EventErrorResponse(code, message));
    }
}