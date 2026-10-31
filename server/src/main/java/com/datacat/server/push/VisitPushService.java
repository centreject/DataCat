package com.datacat.server.push;

import com.datacat.server.event.Event;
import com.google.firebase.messaging.FirebaseMessaging;
import com.google.firebase.messaging.FirebaseMessagingException;
import com.google.firebase.messaging.MessagingErrorCode;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.core.task.TaskExecutor;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.Optional;

@Service
public class VisitPushService {

    private static final Logger log =
            LoggerFactory.getLogger(VisitPushService.class);

    private final PushTokenRepository pushTokenRepository;
    private final Optional<FirebaseMessaging> firebaseMessaging;
    private final TaskExecutor executor;

    public VisitPushService(
            PushTokenRepository pushTokenRepository,
            Optional<FirebaseMessaging> firebaseMessaging,
            @Qualifier("visitPushExecutor") TaskExecutor executor
    ) {
        this.pushTokenRepository = pushTokenRepository;
        this.firebaseMessaging = firebaseMessaging;
        this.executor = executor;
    }

    // 방문 정보를 DB에 저장하고 커밋한 뒤 호출한다.
    public void notifyVisit(Event event) {
        if (firebaseMessaging.isEmpty()) {
            return;
        }

        try {
            VisitPushMessage message =
                    VisitPushMessage.from(event);

            FirebaseMessaging client = firebaseMessaging.get();

            executor.execute(
                    () -> sendToAll(client, message)
            );

        } catch (RuntimeException exception) {
            // 푸시 작업 등록 실패가 방문 접수 응답에 전파되지 않게 한다.
            log.error(
                    "방문 푸시 작업을 등록하지 못했습니다.",
                    exception
            );
        }
    }

    private void sendToAll(
            FirebaseMessaging client,
            VisitPushMessage message
    ) {
        List<PushToken> tokens;

        try {
            tokens = pushTokenRepository.findAll();

        } catch (RuntimeException exception) {
            log.error(
                    "푸시 토큰 조회에 실패했습니다. eventId={}",
                    message.eventId(),
                    exception
            );

            return;
        }

        int accepted = 0;
        int failed = 0;

        for (PushToken token : tokens) {
            if (!"ANDROID".equals(token.getPlatform())) {
                continue;
            }

            try {
                client.send(
                        message.forToken(token.getDeviceToken())
                );

                accepted++;

            } catch (FirebaseMessagingException exception) {
                failed++;

                if (exception.getMessagingErrorCode()
                        == MessagingErrorCode.UNREGISTERED) {

                    removeUnregisteredToken(
                            token,
                            message.eventId()
                    );

                } else {
                    log.warn(
                            "FCM 발송 요청이 실패했습니다. eventId={}, code={}",
                            message.eventId(),
                            exception.getMessagingErrorCode()
                    );
                }

            } catch (RuntimeException exception) {
                failed++;

                log.error(
                        "푸시 처리 중 오류가 발생했습니다. eventId={}",
                        message.eventId(),
                        exception
                );
            }
        }

        log.info(
                "FCM 처리 완료. eventId={}, 접수 성공={}, 실패={}",
                message.eventId(),
                accepted,
                failed
        );
    }

    private void removeUnregisteredToken(
            PushToken token,
            Long eventId
    ) {
        try {
            pushTokenRepository.deleteById(token.getTokenId());

            log.info(
                    "등록 해제된 푸시 토큰을 삭제했습니다. eventId={}",
                    eventId
            );

        } catch (RuntimeException exception) {
            log.error(
                    "등록 해제된 토큰 삭제에 실패했습니다. eventId={}",
                    eventId,
                    exception
            );
        }
    }
}