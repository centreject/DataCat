package com.datacat.server.push;

import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Instant;
import java.util.HexFormat;

@Service
public class PushTokenService {

    private final PushTokenRepository pushTokenRepository;

    public PushTokenService(
            PushTokenRepository pushTokenRepository
    ) {
        this.pushTokenRepository = pushTokenRepository;
    }

    public synchronized void register(PushTokenRequest request) {
        validateRequest(request);

        String tokenId = createTokenId(request.deviceToken());
        Instant registeredAt = Instant.now();

        PushToken token = pushTokenRepository
                .findById(tokenId)
                .orElse(null);

        if (token == null) {
            token = new PushToken(
                    tokenId,
                    request.deviceToken(),
                    request.platform(),
                    registeredAt
            );
        } else {
            token.registerAgain(registeredAt);
        }

        pushTokenRepository.saveAndFlush(token);
    }

    private void validateRequest(PushTokenRequest request) {
        if (request == null
                || request.deviceToken() == null
                || request.deviceToken().isBlank()) {
            throw badRequest(
                    "deviceToken은 비어 있을 수 없습니다."
            );
        }

        if (request.deviceToken().length() > 512) {
            throw badRequest(
                    "deviceToken은 512자 이하여야 합니다."
            );
        }

        if (!"ANDROID".equals(request.platform())) {
            throw badRequest(
                    "platform은 ANDROID여야 합니다."
            );
        }
    }

    private String createTokenId(String deviceToken) {
        try {
            MessageDigest digest =
                    MessageDigest.getInstance("SHA-256");

            byte[] hash = digest.digest(
                    deviceToken.getBytes(StandardCharsets.UTF_8)
            );

            return HexFormat.of().formatHex(hash);

        } catch (NoSuchAlgorithmException exception) {
            throw new IllegalStateException(
                    "토큰 저장용 식별자를 생성할 수 없습니다.",
                    exception
            );
        }
    }

    private ResponseStatusException badRequest(String message) {
        return new ResponseStatusException(
                HttpStatus.BAD_REQUEST,
                message
        );
    }
}