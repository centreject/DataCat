package com.datacat.server.push;

import com.datacat.server.event.Event;
import com.datacat.server.event.EventStatus;
import com.google.firebase.messaging.AndroidConfig;
import com.google.firebase.messaging.AndroidNotification;
import com.google.firebase.messaging.Message;
import com.google.firebase.messaging.Notification;

public record VisitPushMessage(
        Long eventId,
        String title,
        String body
) {

    public static VisitPushMessage from(Event event) {
        if (event == null
                || event.getEventId() == null
                || event.getEventId() < 1) {
            throw new IllegalArgumentException(
                    "저장된 방문 이벤트가 필요합니다."
            );
        }

        String title;
        String body;

        if (event.getStatus() == EventStatus.WAITING_AUDIO) {
            title = "방문객이 왔어요";
            body = "용건을 듣고 있어요";

        } else {
            String main = firstNonBlank(
                    event.getMainCategory(),
                    "새 방문"
            );

            String sub = event.getSubCategory();

            boolean hasSub = sub != null && !sub.isBlank();

            if ("긴급 알림".equals(event.getResponsePolicy())
                    || "공공·긴급 방문".equals(main)
                    || "안전 확인 필요".equals(main)) {

                title = "긴급 · " + (hasSub ? sub : main);

            } else if ("물품만 있음".equals(main)) {
                title = hasSub
                        ? "물품 도착 · " + sub
                        : "물품 도착";

            } else {
                title = "새 방문 · " + main;
            }

            body = firstNonBlank(
                    event.getSummary(),
                    event.getReason(),
                    "방문 기록을 확인해 주세요."
            );
        }

        if (event.getNeedsReview()) {
            body += " (확인 필요)";
        }

        return new VisitPushMessage(
                event.getEventId(),
                title,
                body
        );
    }

    public String tag() {
        return "event_" + eventId;
    }

    public Message forToken(String deviceToken) {
        return Message.builder()
                .setToken(deviceToken)
                .setNotification(
                        Notification.builder()
                                .setTitle(title)
                                .setBody(body)
                                .build()
                )
                .putData("type", "VISIT_EVENT")
                .putData("eventId", eventId.toString())
                .putData("tag", tag())
                .setAndroidConfig(
                        AndroidConfig.builder()
                                .setPriority(AndroidConfig.Priority.HIGH)
                                .setCollapseKey(tag())
                                .setNotification(
                                        AndroidNotification.builder()
                                                .setTag(tag())
                                                .build()
                                )
                                .build()
                )
                .build();
    }

    private static String firstNonBlank(String... values) {
        for (String value : values) {
            if (value != null && !value.isBlank()) {
                return value;
            }
        }

        return "";
    }
}