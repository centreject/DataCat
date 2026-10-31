package com.datacat.server.model;

import com.sun.net.httpserver.HttpServer;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpStatus;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.web.server.ResponseStatusException;

import java.net.InetSocketAddress;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicLong;
import java.util.concurrent.atomic.AtomicReference;

import static org.junit.jupiter.api.Assertions.*;

class AudioModelClientTests {

    private HttpServer server;
    private AudioModelClient client;

    private final AtomicInteger status = new AtomicInteger(200);
    private final AtomicLong delayMillis = new AtomicLong();
    private final AtomicReference<String> response = new AtomicReference<>();
    private final AtomicReference<String> requestBody = new AtomicReference<>();
    private final AtomicReference<String> requestContentType = new AtomicReference<>();
    private final AtomicReference<String> requestMethod = new AtomicReference<>();

    private static final String DELIVERY = """
            {
              "transcript":"택배 왔습니다. 문 앞에 놓고 갈게요.",
              "purpose":"DELIVERY",
              "subtype":"PARCEL",
              "summary":"택배 문 앞 보관",
              "flags":[]
            }
            """;

    @BeforeEach
    void setUp() throws Exception {
        response.set(DELIVERY);
        server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        server.createContext("/internal/v1/audio/process", exchange -> {
            try {
                requestMethod.set(exchange.getRequestMethod());
                requestContentType.set(exchange.getRequestHeaders().getFirst("Content-Type"));
                requestBody.set(new String(
                        exchange.getRequestBody().readAllBytes(), StandardCharsets.UTF_8
                ));

                if (delayMillis.get() > 0) {
                    Thread.sleep(delayMillis.get());
                }

                byte[] bytes = response.get().getBytes(StandardCharsets.UTF_8);
                exchange.getResponseHeaders().set("Content-Type", "application/json");

                if (bytes.length == 0) {
                    exchange.sendResponseHeaders(status.get(), -1);
                } else {
                    exchange.sendResponseHeaders(status.get(), bytes.length);
                    exchange.getResponseBody().write(bytes);
                }
            } catch (InterruptedException exception) {
                Thread.currentThread().interrupt();
            } finally {
                exchange.close();
            }
        });
        server.start();
        client = new AudioModelClient("http://127.0.0.1:" + server.getAddress().getPort(), 5_000);
    }

    @AfterEach
    void tearDown() {
        if (server != null) {
            server.stop(0);
        }
    }

    @Test
    void sendsNamedAudioPartAndReadsModelResult() {
        AudioProcessResponse result = client.process(audio("delivery.wav"));

        assertEquals("POST", requestMethod.get());
        assertTrue(requestContentType.get().startsWith("multipart/form-data;"));
        assertTrue(requestBody.get().contains("name=\"audio\""));
        assertTrue(requestBody.get().contains("filename=\"delivery.wav\""));
        assertTrue(requestBody.get().contains("Content-Type: audio/wav"));
        assertTrue(requestBody.get().contains("RIFF"));
        assertTrue(requestBody.get().contains("WAVE"));
        assertEquals("택배 왔습니다. 문 앞에 놓고 갈게요.", result.transcript());
        assertEquals("DELIVERY", result.purpose());
        assertEquals("PARCEL", result.subtype());
        assertEquals("택배 문 앞 보관", result.summary());
        assertTrue(result.flags().isEmpty());
    }

    @Test
    void suppliesFilenameWhenIncomingNameIsMissing() {
        client.process(audio(""));
        assertTrue(requestBody.get().contains("filename=\"speech.wav\""));
    }

    @Test
    void acceptsNoSpeechResponse() {
        response.set("""
                {"transcript":"","purpose":"UNKNOWN","subtype":null,
                 "summary":"","flags":["NO_SPEECH"]}
                """);
        AudioProcessResponse result = client.process(audio("silent.wav"));
        assertEquals("", result.transcript());
        assertEquals("UNKNOWN", result.purpose());
        assertNull(result.subtype());
        assertEquals("", result.summary());
        assertTrue(result.flags().contains("NO_SPEECH"));
    }

    @Test
    void acceptsDeliveryWithoutSubtype() {
        response.set(DELIVERY.replace("\"PARCEL\"", "null"));
        assertNull(client.process(audio("delivery.wav")).subtype());
    }

    @Test
    void shortensSummaryWithoutSplittingEmoji() {
        response.set(DELIVERY.replace("택배 문 앞 보관", "😀".repeat(21)));
        String summary = client.process(audio("delivery.wav")).summary();
        assertEquals("😀".repeat(19) + "…", summary);
        assertEquals(20, summary.codePointCount(0, summary.length()));
    }

    @Test
    void rejectsUnknownPurpose() {
        response.set(DELIVERY.replace("\"DELIVERY\"", "\"FUTURE_PURPOSE\""));
        assertStatus(HttpStatus.SERVICE_UNAVAILABLE);
    }

    @Test
    void rejectsSubtypeOnNonDeliveryPurpose() {
        response.set(DELIVERY.replace("\"DELIVERY\"", "\"PERSONAL_VISIT\""));
        assertStatus(HttpStatus.SERVICE_UNAVAILABLE);
    }

    @Test
    void rejectsUnknownDeliverySubtype() {
        response.set(DELIVERY.replace("\"PARCEL\"", "\"FUTURE_SUBTYPE\""));
        assertStatus(HttpStatus.SERVICE_UNAVAILABLE);
    }

    @Test
    void rejectsMissingSummary() {
        response.set(DELIVERY.replace("\"summary\":\"택배 문 앞 보관\",", ""));
        assertStatus(HttpStatus.SERVICE_UNAVAILABLE);
    }

    @Test
    void rejectsMissingFlags() {
        response.set(DELIVERY.replace(",\n  \"flags\":[]", ""));
        assertStatus(HttpStatus.SERVICE_UNAVAILABLE);
    }

    @Test
    void rejectsNullFlag() {
        response.set(DELIVERY.replace("\"flags\":[]", "\"flags\":[null]"));
        assertStatus(HttpStatus.SERVICE_UNAVAILABLE);
    }

    @Test
    void rejectsNoSpeechFlagWithNonemptyTranscript() {
        response.set(DELIVERY.replace("\"flags\":[]", "\"flags\":[\"NO_SPEECH\"]"));
        assertStatus(HttpStatus.SERVICE_UNAVAILABLE);
    }

    @Test
    void mapsModelBadRequestTo400() {
        status.set(400);
        response.set("{\"code\":\"INVALID_AUDIO\",\"message\":\"invalid WAV\"}");
        assertStatus(HttpStatus.BAD_REQUEST);
    }

    @Test
    void mapsModelUnavailableTo503() {
        status.set(503);
        response.set("{\"code\":\"MODEL_NOT_READY\",\"message\":\"loading\"}");
        assertStatus(HttpStatus.SERVICE_UNAVAILABLE);
    }

    @Test
    void mapsMalformedJsonTo503() {
        response.set("{invalid JSON");
        assertStatus(HttpStatus.SERVICE_UNAVAILABLE);
    }

    @Test
    void rejectsEmptyModelBody() {
        response.set("");
        assertStatus(HttpStatus.SERVICE_UNAVAILABLE);
    }

    @Test
    void mapsConnectionFailureTo503() {
        server.stop(0);
        server = null;
        assertStatus(HttpStatus.SERVICE_UNAVAILABLE);
    }

    @Test
    void mapsReadTimeoutTo503() {
        delayMillis.set(5_500);
        assertStatus(HttpStatus.SERVICE_UNAVAILABLE);
    }

    @Test
    void acceptsSlowResponseWithTenSecondReadTimeout() {
        client = new AudioModelClient("http://127.0.0.1:" + server.getAddress().getPort(), 10_000);
        delayMillis.set(8_500);

        AudioProcessResponse result = client.process(audio("delivery.wav"));

        assertEquals("DELIVERY", result.purpose());
        assertEquals("택배 문 앞 보관", result.summary());
    }

    @Test
    void rejectsUnboundedOrNegativeReadTimeout() {
        String baseUrl = "http://127.0.0.1:" + server.getAddress().getPort();
        assertThrows(IllegalArgumentException.class, () -> new AudioModelClient(baseUrl, 0));
        assertThrows(IllegalArgumentException.class, () -> new AudioModelClient(baseUrl, -1));
    }

    @Test
    void rejectsMissingAudioBeforeSendingRequest() {
        ResponseStatusException exception = assertThrows(
                ResponseStatusException.class, () -> client.process(null)
        );
        assertEquals(HttpStatus.BAD_REQUEST, exception.getStatusCode());
        assertNull(requestBody.get());
    }

    @Test
    void rejectsEmptyAudioBeforeSendingRequest() {
        MockMultipartFile empty = new MockMultipartFile("audio", new byte[0]);
        ResponseStatusException exception = assertThrows(
                ResponseStatusException.class, () -> client.process(empty)
        );
        assertEquals(HttpStatus.BAD_REQUEST, exception.getStatusCode());
        assertNull(requestBody.get());
    }

    @Test
    void rejectsOversizedAudioBeforeSendingRequest() {
        MockMultipartFile oversized = new MockMultipartFile(
                "audio", "large.wav", "audio/wav", new byte[16 * 1024 * 1024 + 1]
        );
        ResponseStatusException exception = assertThrows(
                ResponseStatusException.class, () -> client.process(oversized)
        );
        assertEquals(HttpStatus.BAD_REQUEST, exception.getStatusCode());
        assertNull(requestBody.get());
    }

    @Test
    void toleratesExtraJsonFieldAndPreservesUnknownFlagWithoutInterpretingIt() {
        response.set(DELIVERY.replace("\"flags\":[]",
                "\"flags\":[\"FUTURE_FLAG\"],\"extraInfo\":\"ignored\""));
        AudioProcessResponse result = client.process(audio("delivery.wav"));
        assertEquals("DELIVERY", result.purpose());
        assertTrue(result.flags().contains("FUTURE_FLAG"));
    }

    private void assertStatus(HttpStatus expected) {
        ResponseStatusException exception = assertThrows(
                ResponseStatusException.class, () -> client.process(audio("delivery.wav"))
        );
        assertEquals(expected, exception.getStatusCode());
    }

    private MockMultipartFile audio(String filename) {
        // 16kHz, mono, PCM 16-bit WAV: 10ms 무음. 실제 모델은 호출하지 않는다.
        ByteBuffer wav = ByteBuffer.allocate(44 + 320).order(ByteOrder.LITTLE_ENDIAN);
        wav.put("RIFF".getBytes(StandardCharsets.US_ASCII));
        wav.putInt(36 + 320);
        wav.put("WAVEfmt ".getBytes(StandardCharsets.US_ASCII));
        wav.putInt(16);
        wav.putShort((short) 1);
        wav.putShort((short) 1);
        wav.putInt(16_000);
        wav.putInt(32_000);
        wav.putShort((short) 2);
        wav.putShort((short) 16);
        wav.put("data".getBytes(StandardCharsets.US_ASCII));
        wav.putInt(320);
        return new MockMultipartFile("audio", filename, "audio/wav", wav.array());
    }
}
