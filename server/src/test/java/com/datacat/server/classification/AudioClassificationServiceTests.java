package com.datacat.server.classification;

import com.datacat.server.model.AudioProcessResponse;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;
import org.junit.jupiter.params.provider.ValueSource;

import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

class AudioClassificationServiceTests {

    private final AudioClassificationService service = new AudioClassificationService();

    @ParameterizedTest
    @CsvSource({
            "PUBLIC_EMERGENCY, 공공·긴급 방문, 긴급 알림, false",
            "SAFETY_REVIEW, 안전 확인 필요, 긴급 알림, true",
            "PICKUP, 수거, 일반 접수, false",
            "WRONG_VISIT, 잘못 방문, 일반 접수, false",
            "DELIVERY, 배송, 일반 접수, false",
            "SERVICE_VISIT, 작업 방문, 일반 접수, true",
            "PERSONAL_VISIT, 개인 방문, 일반 접수, false",
            "SOLICITATION, 영업·홍보 방문, 일반 접수, false",
            "UNKNOWN, 기타·판단 불가, 일반 접수, false"
    })
    void mapsAllNinePurposesAccordingToTableC(
            String purpose, String category, String policy, boolean needsReview
    ) {
        AudioClassificationResult result = service.classify(
                response(purpose, null, List.of()), "정상", false
        );
        assertEquals("VISITOR_ACCEPTED", result.eventType());
        assertEquals(category, result.mainCategory());
        assertEquals(policy, result.responsePolicy());
        assertEquals(needsReview, result.needsReview());
        assertEquals("정상", result.processingStatus());

        if (!"DELIVERY".equals(purpose)) {
            assertNull(result.subCategory());
        }
    }

    @ParameterizedTest
    @CsvSource({
            "PARCEL, 택배",
            "FOOD, 음식 배달",
            "MAIL, 우편·등기",
            "GROCERY, 장보기·생활물품",
            "QUICK, 퀵 배송",
            "LARGE, 대형 상품",
            "GIFT, 선물 배송",
            "OTHER, 배송 기타"
    })
    void mapsAllEightDeliverySubtypes(String subtype, String category) {
        AudioClassificationResult result = service.classify(
                response("DELIVERY", subtype, List.of()), "정상", false
        );
        assertEquals("배송", result.mainCategory());
        assertEquals(category, result.subCategory());
        assertEquals("용건: 배송(" + category + ")", result.reason());
    }

    @Test
    void missingDeliverySubtypeUsesOtherDelivery() {
        AudioClassificationResult result = service.classify(
                response("DELIVERY", null, List.of()), "정상", false
        );
        assertEquals("배송 기타", result.subCategory());
        assertEquals("용건: 배송(배송 기타)", result.reason());
    }

    @Test
    void noSpeechIsUnansweredWithoutAddingReviewFlag() {
        AudioClassificationResult result = service.classify(noSpeech(), "정상", false);
        assertEquals("VISITOR_ACCEPTED", result.eventType());
        assertEquals("기타·판단 불가", result.mainCategory());
        assertEquals("무응답", result.processingStatus());
        assertFalse(result.needsReview());
    }

    @ParameterizedTest
    @ValueSource(strings = {"SUMMARY_FROM_TRANSCRIPT", "RULES_FALLBACK"})
    void languageFallbackRequiresReview(String flag) {
        AudioClassificationResult result = service.classify(
                response("PERSONAL_VISIT", null, List.of(flag)), "정상", false
        );
        assertEquals("정상", result.processingStatus());
        assertTrue(result.needsReview());
    }

    @Test
    void keepsReviewFlagFromPhotoStage() {
        AudioClassificationResult result = service.classify(
                response("DELIVERY", "PARCEL", List.of()), "정상", true
        );
        assertTrue(result.needsReview());
        assertEquals("배송", result.mainCategory());
    }

    @Test
    void imageFailureRemainsEvenWhenAudioHasNoSpeech() {
        AudioClassificationResult result = service.classify(
                noSpeech(), "이미지 판단 실패", true
        );
        assertEquals("이미지 판단 실패", result.processingStatus());
        assertTrue(result.needsReview());
    }

    @Test
    void imageFailureRemainsAfterSuccessfulLanguageAnalysis() {
        AudioClassificationResult result = service.classify(
                response("DELIVERY", "PARCEL", List.of()), "이미지 판단 실패", true
        );
        assertEquals("배송", result.mainCategory());
        assertEquals("이미지 판단 실패", result.processingStatus());
        assertTrue(result.needsReview());
    }

    @Test
    void multipleVisitorsRemainWhenNoKnownFlagOverridesStatus() {
        AudioClassificationResult result = service.classify(
                response("PERSONAL_VISIT", null, List.of()), "복수 방문자", false
        );
        assertEquals("복수 방문자", result.processingStatus());
        assertFalse(result.needsReview());
    }

    @Test
    void languageFallbackOnMultipleVisitorsFollowsNormalStatusRow() {
        AudioClassificationResult result = service.classify(
                response("PERSONAL_VISIT", null, List.of("RULES_FALLBACK")),
                "복수 방문자", false
        );
        assertEquals("정상", result.processingStatus());
        assertTrue(result.needsReview());
    }

    @Test
    void noSpeechOnMultipleVisitorsIsUnanswered() {
        AudioClassificationResult result = service.classify(noSpeech(), "복수 방문자", false);
        assertEquals("무응답", result.processingStatus());
        assertFalse(result.needsReview());
    }

    @Test
    void combinesFlagsWithoutLosingNeedForReview() {
        AudioProcessResponse response = new AudioProcessResponse(
                "", "UNKNOWN", null, "", List.of("NO_SPEECH", "RULES_FALLBACK")
        );
        AudioClassificationResult result = service.classify(response, "정상", false);
        assertEquals("무응답", result.processingStatus());
        assertTrue(result.needsReview());
    }

    @Test
    void unknownFlagDoesNotInventAnotherClassificationRule() {
        AudioClassificationResult result = service.classify(
                response("PERSONAL_VISIT", null, List.of("FUTURE_FLAG")),
                "복수 방문자", false
        );
        assertEquals("개인 방문", result.mainCategory());
        assertEquals("복수 방문자", result.processingStatus());
        assertFalse(result.needsReview());
    }

    @Test
    void missingPhotoStatusDefaultsToNormal() {
        AudioClassificationResult result = service.classify(
                response("PICKUP", null, List.of()), null, false
        );
        assertEquals("정상", result.processingStatus());
        assertEquals("용건: 수거", result.reason());
    }

    @Test
    void rejectsUnvalidatedUnknownPurpose() {
        assertThrows(IllegalArgumentException.class, () -> service.classify(
                response("FUTURE_PURPOSE", null, List.of()), "정상", false
        ));
    }

    @Test
    void rejectsMissingModelResponse() {
        assertThrows(IllegalArgumentException.class,
                () -> service.classify(null, "정상", false));
    }

    private AudioProcessResponse response(String purpose, String subtype, List<String> flags) {
        return new AudioProcessResponse("방문객 발화", purpose, subtype, "요약", flags);
    }

    private AudioProcessResponse noSpeech() {
        return new AudioProcessResponse("", "UNKNOWN", null, "", List.of("NO_SPEECH"));
    }
}
