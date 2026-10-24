package com.datacat.server.storage;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.io.Resource;
import org.springframework.core.io.UrlResource;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.server.ResponseStatusException;

import javax.imageio.ImageIO;
import javax.imageio.ImageReader;
import javax.imageio.stream.MemoryCacheImageInputStream;
import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.util.Iterator;
import java.util.UUID;

@Service
public class SnapshotStorageService {

    private static final long MAX_FILE_SIZE = 16L * 1024 * 1024;
    private static final long MAX_PIXELS = 40_000_000L;

    private final Path rootDirectory;

    public SnapshotStorageService(
            @Value("${datacat.storage.snapshot-dir}") String directory
    ) {
        this.rootDirectory = Path.of(directory)
                .toAbsolutePath()
                .normalize();
    }

    public String save(MultipartFile image) {
        if (image == null || image.isEmpty()) {
            throw new ResponseStatusException(
                    HttpStatus.BAD_REQUEST,
                    "이미지 파일이 비어 있습니다."
            );
        }

        if (image.getSize() > MAX_FILE_SIZE) {
            throw new ResponseStatusException(
                    HttpStatus.BAD_REQUEST,
                    "이미지 파일은 16MB 이하여야 합니다."
            );
        }

        if (!"image/jpeg".equalsIgnoreCase(image.getContentType())) {
            throw new ResponseStatusException(
                    HttpStatus.BAD_REQUEST,
                    "이미지는 image/jpeg 형식이어야 합니다."
            );
        }

        try {
            byte[] bytes = image.getBytes();

            validateJpeg(bytes);

            Files.createDirectories(rootDirectory);

            String filename = UUID.randomUUID() + ".jpg";
            Path target = rootDirectory.resolve(filename);

            Files.write(
                    target,
                    bytes,
                    StandardOpenOption.CREATE_NEW,
                    StandardOpenOption.WRITE
            );

            return filename;
        } catch (IOException exception) {
            throw new ResponseStatusException(
                    HttpStatus.INTERNAL_SERVER_ERROR,
                    "이미지 파일 저장에 실패했습니다.",
                    exception
            );
        }
    }

    public Resource load(String snapshotPath) {
        if (snapshotPath == null || snapshotPath.isBlank()) {
            throw new ResponseStatusException(
                    HttpStatus.NOT_FOUND,
                    "해당 이벤트에 저장된 사진이 없습니다."
            );
        }

        Path target = resolveStoredPath(snapshotPath);

        if (!Files.isRegularFile(target) || !Files.isReadable(target)) {
            throw new ResponseStatusException(
                    HttpStatus.NOT_FOUND,
                    "사진 파일을 찾을 수 없습니다."
            );
        }

        try {
            return new UrlResource(target.toUri());
        } catch (IOException exception) {
            throw new ResponseStatusException(
                    HttpStatus.INTERNAL_SERVER_ERROR,
                    "사진 파일을 읽을 수 없습니다.",
                    exception
            );
        }
    }

    public void delete(String snapshotPath) {
        Path target = resolveStoredPath(snapshotPath);

        try {
            Files.deleteIfExists(target);
        } catch (IOException exception) {
            throw new ResponseStatusException(
                    HttpStatus.INTERNAL_SERVER_ERROR,
                    "이미지 파일 정리에 실패했습니다.",
                    exception
            );
        }
    }

    private Path resolveStoredPath(String snapshotPath) {
        Path target = rootDirectory.resolve(snapshotPath).normalize();

        if (!rootDirectory.equals(target.getParent())) {
            throw new ResponseStatusException(
                    HttpStatus.INTERNAL_SERVER_ERROR,
                    "저장된 사진 경로가 올바르지 않습니다."
            );
        }

        return target;
    }

    private void validateJpeg(byte[] bytes) {
        try (MemoryCacheImageInputStream input =
                     new MemoryCacheImageInputStream(
                             new ByteArrayInputStream(bytes)
                     )) {

            Iterator<ImageReader> readers = ImageIO.getImageReaders(input);

            if (!readers.hasNext()) {
                throw invalidImage();
            }

            ImageReader reader = readers.next();

            try {
                if (!"JPEG".equalsIgnoreCase(reader.getFormatName())) {
                    throw invalidImage();
                }

                reader.setInput(input);

                int width = reader.getWidth(0);
                int height = reader.getHeight(0);

                if (width < 1 || height < 1
                        || (long) width * height > MAX_PIXELS) {
                    throw new ResponseStatusException(
                            HttpStatus.BAD_REQUEST,
                            "이미지 해상도는 40MP 이하여야 합니다."
                    );
                }

                if (reader.read(0) == null) {
                    throw invalidImage();
                }
            } finally {
                reader.dispose();
            }
        } catch (IOException exception) {
            throw invalidImage();
        }
    }

    private ResponseStatusException invalidImage() {
        return new ResponseStatusException(
                HttpStatus.BAD_REQUEST,
                "읽을 수 있는 JPEG 이미지 파일이 필요합니다."
        );
    }
}