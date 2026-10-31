package com.datacat.server.device;

import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestPart;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

@RestController
@RequestMapping("/api/v1/device/events")
public class DeviceEventController {

    private final DeviceEventService deviceEventService;

    public DeviceEventController(
            DeviceEventService deviceEventService
    ) {
        this.deviceEventService = deviceEventService;
    }

    @PostMapping(
            value = "/{eventId}/audio",
            consumes = MediaType.MULTIPART_FORM_DATA_VALUE
    )
    public DeviceEventResponse receiveAudio(
            @PathVariable("eventId") Long eventId,
            @RequestPart("audio") MultipartFile audio
    ) {
        return deviceEventService.receiveAudio(eventId, audio);
    }

    @PostMapping(
            value = "/{eventId}/end",
            consumes = MediaType.APPLICATION_JSON_VALUE
    )
    public DeviceEventResponse endEvent(
            @PathVariable("eventId") Long eventId,
            @RequestBody DeviceEndRequest request
    ) {
        return deviceEventService.endEvent(eventId, request);
    }

    @PostMapping(consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public ResponseEntity<DeviceEventResponse> createEvent(
            @RequestPart("metadata") DeviceEventMetadata metadata,
            @RequestPart("image") MultipartFile image
    ) {
        DeviceEventService.CreationResult result =
                deviceEventService.createEvent(metadata, image);

        HttpStatus status = result.created()
                ? HttpStatus.CREATED
                : HttpStatus.OK;

        return ResponseEntity
                .status(status)
                .body(result.response());
    }
}
