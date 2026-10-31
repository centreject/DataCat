package com.datacat.server.model;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;

import java.util.List;

@JsonIgnoreProperties(ignoreUnknown = true)
public record AudioProcessResponse(
        String transcript,
        String purpose,
        String subtype,
        String summary,
        List<String> flags
) {
}