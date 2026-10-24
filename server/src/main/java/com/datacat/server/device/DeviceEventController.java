package com.datacat.server.device;

import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
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