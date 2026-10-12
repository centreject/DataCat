package com.datacat.server.model;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;

import java.util.List;

@JsonIgnoreProperties(ignoreUnknown = true)
public record VisionResponse(
        List<Detection> detections,
        List<String> flags
) {

    @JsonIgnoreProperties(ignoreUnknown = true)
    public record Detection(
            String label,
            Double confidence
    ) {
    }
}