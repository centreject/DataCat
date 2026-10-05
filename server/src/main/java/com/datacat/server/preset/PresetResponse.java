package com.datacat.server.preset;

public class PresetResponse {

    private final Long presetId;
    private final String type;
    private final String text;

    public PresetResponse(Long presetId, String type, String text) {
        this.presetId = presetId;
        this.type = type;
        this.text = text;
    }

    public Long getPresetId() {
        return presetId;
    }

    public String getType() {
        return type;
    }

    public String getText() {
        return text;
    }
}