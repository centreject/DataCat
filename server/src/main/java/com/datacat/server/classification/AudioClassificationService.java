package com.datacat.server.classification;

import com.datacat.server.model.AudioProcessResponse;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class AudioClassificationService {

    // imageProcessingStatus와 imageNeedsReview는 사진 단계의 값이다.
    // 음성 재분석 시에도 이전 음성 판정값 대신 원래 사진 단계의 값을 전달한다.
    public AudioClassificationResult classify(
            AudioProcessResponse response,
            String imageProcessingStatus,
            boolean imageNeedsReview
    ) {
        if (response == null
                || response.transcript() == null
                || response.purpose() == null
                || response.summary() == null
                || response.flags() == null) {
            throw new IllegalArgumentException("검증된 음성 분석 결과가 필요합니다.");
        }

        String mainCategory = switch (response.purpose()) {
            case "PUBLIC_EMERGENCY" -> "공공·긴급 방문";
            case "SAFETY_REVIEW" -> "안전 확인 필요";
            case "PICKUP" -> "수거";
            case "WRONG_VISIT" -> "잘못 방문";
            case "DELIVERY" -> "배송";
            case "SERVICE_VISIT" -> "작업 방문";
            case "PERSONAL_VISIT" -> "개인 방문";
            case "SOLICITATION" -> "영업·홍보 방문";
            case "UNKNOWN" -> "기타·판단 불가";
            default -> throw new IllegalArgumentException(
                    "지원하지 않는 용건입니다: " + response.purpose()
            );
        };

        String subCategory = "DELIVERY".equals(response.purpose())
                ? deliveryCategory(response.subtype())
                : null;

        boolean urgent = "PUBLIC_EMERGENCY".equals(response.purpose())
                || "SAFETY_REVIEW".equals(response.purpose());

        boolean purposeNeedsReview = "SAFETY_REVIEW".equals(response.purpose())
                || "SERVICE_VISIT".equals(response.purpose());

        List<String> flags = response.flags();
        boolean noSpeech = flags.contains("NO_SPEECH");
        boolean fallback = flags.contains("SUMMARY_FROM_TRANSCRIPT")
                || flags.contains("RULES_FALLBACK");
        boolean imageFailed = "이미지 판단 실패".equals(imageProcessingStatus);

        String processingStatus;

        if (imageFailed) {
            // A0으로 시작한 방문은 이미지 판단 실패 표시를 유지한다.
            processingStatus = "이미지 판단 실패";
        } else if (noSpeech) {
            processingStatus = "무응답";
        } else if (fallback) {
            // 판정표 C: 요약 대체·규칙 대체 시 처리 상태는 정상, 확인 필요는 true다.
            processingStatus = "정상";
        } else if ("복수 방문자".equals(imageProcessingStatus)) {
            processingStatus = "복수 방문자";
        } else {
            processingStatus = "정상";
        }

        boolean needsReview = imageNeedsReview
                || imageFailed
                || purposeNeedsReview
                || fallback;

        String reason = "용건: " + mainCategory;

        if (subCategory != null) {
            reason += "(" + subCategory + ")";
        }

        return new AudioClassificationResult(
                "VISITOR_ACCEPTED",
                mainCategory,
                subCategory,
                urgent ? "긴급 알림" : "일반 접수",
                processingStatus,
                reason,
                needsReview
        );
    }

    private String deliveryCategory(String subtype) {
        if (subtype == null) {
            return "배송 기타";
        }

        return switch (subtype) {
            case "PARCEL" -> "택배";
            case "FOOD" -> "음식 배달";
            case "MAIL" -> "우편·등기";
            case "GROCERY" -> "장보기·생활물품";
            case "QUICK" -> "퀵 배송";
            case "LARGE" -> "대형 상품";
            case "GIFT" -> "선물 배송";
            case "OTHER" -> "배송 기타";
            default -> throw new IllegalArgumentException(
                    "지원하지 않는 배송 세부 유형입니다: " + subtype
            );
        };
    }
}
