package com.datacat.server.push;

import com.datacat.server.event.EventExceptionHandler;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.ResultActions;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;
import java.util.Locale;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest
@ActiveProfiles("test")
@Transactional
class PushTokenRegistrationTests {

    @Autowired
    private PushTokenService pushTokenService;

    @Autowired
    private PushTokenRepository pushTokenRepository;

    private MockMvc mockMvc;

    @BeforeEach
    void setUp() {
        mockMvc = MockMvcBuilders
                .standaloneSetup(
                        new PushTokenController(pushTokenService)
                )
                .setControllerAdvice(new EventExceptionHandler())
                .build();
    }

    @Test
    void registersNewToken() throws Exception {
        String token = "test-token-" + UUID.randomUUID();
        long countBefore = pushTokenRepository.count();

        register(token, "ANDROID")
                .andExpect(status().isCreated())
                .andExpect(content().string(""));

        PushToken saved = findToken(token);

        assertEquals(countBefore + 1, pushTokenRepository.count());
        assertEquals(token, saved.getDeviceToken());
        assertEquals("ANDROID", saved.getPlatform());
    }

    @Test
    void registeringSameTokenDoesNotCreateAnotherRow() throws Exception {
        String token = "test-token-" + UUID.randomUUID();
        long countBefore = pushTokenRepository.count();

        register(token, "ANDROID")
                .andExpect(status().isCreated());

        Instant firstCreatedAt = findToken(token).getCreatedAt();

        register(token, "ANDROID")
                .andExpect(status().isCreated());

        assertEquals(countBefore + 1, pushTokenRepository.count());

        assertEquals(
                firstCreatedAt,
                findToken(token).getCreatedAt()
        );
    }

    @Test
    void tokensAreCaseSensitive() throws Exception {
        String firstToken = "case-test-Abc-" + UUID.randomUUID();
        String secondToken = firstToken.toLowerCase(Locale.ROOT);
        long countBefore = pushTokenRepository.count();

        register(firstToken, "ANDROID")
                .andExpect(status().isCreated());

        register(secondToken, "ANDROID")
                .andExpect(status().isCreated());

        assertEquals(countBefore + 2, pushTokenRepository.count());

        assertEquals(
                firstToken,
                findToken(firstToken).getDeviceToken()
        );

        assertEquals(
                secondToken,
                findToken(secondToken).getDeviceToken()
        );
    }

    @Test
    void rejectsBlankToken() throws Exception {
        register(" ", "ANDROID")
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value("INVALID_REQUEST"));
    }

    @Test
    void rejectsTooLongToken() throws Exception {
        register("x".repeat(513), "ANDROID")
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value("INVALID_REQUEST"));
    }

    @Test
    void rejectsUnsupportedPlatform() throws Exception {
        register(
                "test-token-" + UUID.randomUUID(),
                "IOS"
        )
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value("INVALID_REQUEST"));
    }

    private ResultActions register(
            String token,
            String platform
    ) throws Exception {
        String json = """
                {
                  "deviceToken": "%s",
                  "platform": "%s"
                }
                """.formatted(token, platform);

        return mockMvc.perform(
                post("/api/v1/push-tokens")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(json)
        );
    }

    private PushToken findToken(String deviceToken) {
        return pushTokenRepository.findAll().stream()
                .filter(token ->
                        deviceToken.equals(token.getDeviceToken())
                )
                .findFirst()
                .orElseThrow();
    }
}