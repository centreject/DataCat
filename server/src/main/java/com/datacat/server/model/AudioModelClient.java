package com.datacat.server.model;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.io.ByteArrayResource;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.stereotype.Component;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.MultiValueMap;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;
import org.springframework.web.client.RestClientResponseException;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.server.ResponseStatusException;

import java.io.IOException;
import java.util.Arrays;
import java.util.List;
import java.util.Set;

@Component
public class AudioModelClient {

    private static final Logger log = LoggerFactory.getLogger(AudioModelClient.class);
    private static final long MAX_FILE_SIZE = 16L * 1024 * 1024;

    private static final Set<String> PURPOSES = Set.of(
            "PUBLIC_EMERGENCY", "SAFETY_REVIEW", "PICKUP", "WRONG_VISIT",
            "DELIVERY", "SERVICE_VISIT", "PERSONAL_VISIT", "SOLICITATION", "UNKNOWN"
    );

    private static final Set<String> DELIVERY_SUBTYPES = Set.of(
            "PARCEL", "FOOD", "MAIL", "GROCERY", "QUICK", "LARGE", "GIFT", "OTHER"
    );

    private final RestClient restClient;

    public AudioModelClient(
            @Value("${datacat.model.base-url}") String baseUrl
    ) {
        SimpleClientHttpRequestFactory requestFactory =
                new SimpleClientHttpRequestFactory();

        requestFactory.setConnectTimeout(2_000);
        requestFactory.setReadTimeout(5_000);

        this.restClient = RestClient.builder()
                .baseUrl(baseUrl)
                .requestFactory(requestFactory)
                .build();
    }

    public AudioProcessResponse process(MultipartFile audio) {
        if (audio == null || audio.isEmpty()) {
            throw new ResponseStatusException(
                    HttpStatus.BAD_REQUEST,
                    "음성 파일이 비어 있습니다."
            );
        }

        if (audio.getSize() > MAX_FILE_SIZE) {
            throw new ResponseStatusException(
                    HttpStatus.BAD_REQUEST,
                    "음성 파일은 16MB 이하여야 합니다."
            );
        }

        byte[] audioBytes = null;

        try {
            audioBytes = audio.getBytes();

            // 파일 이름이 있어야 모델 서비스가 파일 파트로 받을 수 있다.
            ByteArrayResource resource = new ByteArrayResource(audioBytes) {
                @Override
                public String getFilename() {
                    String filename = audio.getOriginalFilename();
                    return filename == null || filename.isBlank()
                            ? "speech.wav"
                            : filename;
                }
            };

            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.parseMediaType("audio/wav"));

            HttpEntity<ByteArrayResource> audioPart =
                    new HttpEntity<>(resource, headers);

            MultiValueMap<String, Object> body = new LinkedMultiValueMap<>();
            body.add("audio", audioPart);

            AudioProcessResponse response = restClient.post()
                    .uri("/internal/v1/audio/process")
                    .contentType(MediaType.MULTIPART_FORM_DATA)
                    .accept(MediaType.APPLICATION_JSON)
                    .body(body)
                    .retrieve()
                    .body(AudioProcessResponse.class);

            validateResponse(response);

            return new AudioProcessResponse(
                    response.transcript(),
                    response.purpose(),
                    response.subtype(),
                    shortenSummary(response.summary()),
                    List.copyOf(response.flags())
            );

        } catch (IOException exception) {
            throw new ResponseStatusException(
                    HttpStatus.INTERNAL_SERVER_ERROR,
                    "모델에 전달할 음성 파일을 읽을 수 없습니다.",
                    exception
            );

        } catch (RestClientResponseException exception) {
            if (exception.getStatusCode().value() == 400) {
                throw new ResponseStatusException(
                        HttpStatus.BAD_REQUEST,
                        "음성 파일의 형식 또는 크기를 확인해 주세요. "
                                + "필요한 형식은 WAV PCM 16-bit, 16kHz, mono입니다.",
                        exception
                );
            }

            log.warn("음성 모델 서비스 HTTP 오류. status={}",
                    exception.getStatusCode().value());
            throw unavailable(exception);

        } catch (RestClientException exception) {
            // 원본 음성과 전사문을 로그에 남기지 않는다.
            log.warn("음성 모델 서비스 호출 실패. type={}",
                    exception.getClass().getSimpleName());
            throw unavailable(exception);

        } finally {
            // 이 메서드가 읽은 배열만 비운다. multipart 임시 파일 정리와는 별개다.
            if (audioBytes != null) {
                Arrays.fill(audioBytes, (byte) 0);
            }
        }
    }

    private void validateResponse(AudioProcessResponse response) {
        if (response == null
                || response.transcript() == null
                || response.purpose() == null
                || !PURPOSES.contains(response.purpose())
                || response.summary() == null
                || response.flags() == null) {
            throw invalidResponse();
        }

        if (response.subtype() != null
                && (!"DELIVERY".equals(response.purpose())
                || !DELIVERY_SUBTYPES.contains(response.subtype()))) {
            throw invalidResponse();
        }

        for (String flag : response.flags()) {
            if (flag == null || flag.isBlank()) {
                throw invalidResponse();
            }
        }

        boolean noSpeech = response.flags().contains("NO_SPEECH");

        if (noSpeech) {
            if (!response.transcript().isBlank()
                    || !response.summary().isBlank()
                    || !"UNKNOWN".equals(response.purpose())
                    || response.subtype() != null) {
                throw invalidResponse();
            }
        } else if (response.transcript().isBlank()) {
            throw invalidResponse();
        }
    }

    private String shortenSummary(String summary) {
        if (summary.codePointCount(0, summary.length()) <= 20) {
            return summary;
        }

        int endIndex = summary.offsetByCodePoints(0, 19);
        return summary.substring(0, endIndex) + "…";
    }

    private ResponseStatusException invalidResponse() {
        return new ResponseStatusException(
                HttpStatus.SERVICE_UNAVAILABLE,
                "음성 분석 서비스의 응답 형식이 올바르지 않습니다."
        );
    }

    private ResponseStatusException unavailable(Exception cause) {
        return new ResponseStatusException(
                HttpStatus.SERVICE_UNAVAILABLE,
                "음성 분석 서비스에 연결하거나 응답을 받을 수 없습니다.",
                cause
        );
    }
}
