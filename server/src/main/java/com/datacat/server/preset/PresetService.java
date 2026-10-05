package com.datacat.server.preset;

import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class PresetService {

    public List<PresetResponse> getPresets() {
        return List.of(
                new PresetResponse(
                        1L,
                        "GREETING",
                        "마이크에 말씀해 주세요."
                ),
                new PresetResponse(
                        2L,
                        "COMPLETION",
                        "접수되었습니다."
                )
        );
    }
}