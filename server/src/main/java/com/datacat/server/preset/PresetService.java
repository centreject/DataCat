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
                ),
                new PresetResponse(
                        3L,
                        "FALLBACK",
                        "일시적인 오류로 접수할 수 없습니다. 잠시 후 다시 시도해 주세요."
                )
        );
    }
}