package com.datacat.server.push;

import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/push-tokens")
public class PushTokenController {

    private final PushTokenService pushTokenService;

    public PushTokenController(
            PushTokenService pushTokenService
    ) {
        this.pushTokenService = pushTokenService;
    }

    @PostMapping(consumes = MediaType.APPLICATION_JSON_VALUE)
    public ResponseEntity<Void> register(
            @RequestBody PushTokenRequest request
    ) {
        pushTokenService.register(request);

        return ResponseEntity
                .status(HttpStatus.CREATED)
                .build();
    }
}