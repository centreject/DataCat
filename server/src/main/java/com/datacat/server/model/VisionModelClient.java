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
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.server.ResponseStatusException;

import java.io.IOException;

@Component
public class VisionModelClient {

    private static final Logger log =
            LoggerFactory.getLogger(VisionModelClient.class);

    private final RestClient restClient;

    public VisionModelClient(
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

    public VisionResponse detect(MultipartFile image) {
        try {
            ByteArrayResource imageResource =
                    new ByteArrayResource(image.getBytes()) {
                        @Override
                        public String getFilename() {
                            String filename = image.getOriginalFilename();

                            if (filename == null || filename.isBlank()) {
                                return "snapshot.jpg";
                            }

                            return filename;
                        }
                    };

            HttpHeaders imageHeaders = new HttpHeaders();
            imageHeaders.setContentType(MediaType.IMAGE_JPEG);

            HttpEntity<ByteArrayResource> imagePart =
                    new HttpEntity<>(imageResource, imageHeaders);

            MultiValueMap<String, Object> body =
                    new LinkedMultiValueMap<>();

            body.add("image", imagePart);

            VisionResponse response = restClient.post()
                    .uri("/internal/v1/vision/detect")
                    .contentType(MediaType.MULTIPART_FORM_DATA)
                    .accept(MediaType.APPLICATION_JSON)
                    .body(body)
                    .retrieve()
                    .body(VisionResponse.class);

            validateResponse(response);

            return response;
        } catch (IOException exception) {
            throw new ResponseStatusException(
                    HttpStatus.INTERNAL_SERVER_ERROR,
                    "모델에 전달할 이미지 파일을 읽을 수 없습니다.",
                    exception
            );
        } catch (RestClientException exception) {
            log.warn("Vision 모델 서비스 호출에 실패했습니다.", exception);

            throw new ResponseStatusException(
                    HttpStatus.SERVICE_UNAVAILABLE,
                    "이미지 분석 서비스에 연결하거나 응답을 받을 수 없습니다.",
                    exception
            );
        }
    }

    private void validateResponse(VisionResponse response) {
        if (response == null || response.detections() == null) {
            throw invalidResponse();
        }

        for (VisionResponse.Detection detection : response.detections()) {
            if (detection == null
                    || detection.label() == null
                    || detection.label().isBlank()
                    || detection.confidence() == null
                    || !Double.isFinite(detection.confidence())
                    || detection.confidence() < 0
                    || detection.confidence() > 1) {
                throw invalidResponse();
            }
        }
    }

    private ResponseStatusException invalidResponse() {
        return new ResponseStatusException(
                HttpStatus.SERVICE_UNAVAILABLE,
                "이미지 분석 서비스의 응답 형식이 올바르지 않습니다."
        );
    }
}