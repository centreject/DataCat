package com.datacat.server.push;

import com.google.auth.oauth2.GoogleCredentials;
import com.google.firebase.FirebaseApp;
import com.google.firebase.FirebaseOptions;
import com.google.firebase.messaging.FirebaseMessaging;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;

@Configuration
@ConditionalOnProperty(
        prefix = "datacat.push",
        name = "enabled",
        havingValue = "true"
)
public class FirebaseConfig {

    @Bean(destroyMethod = "delete")
    public FirebaseApp firebaseApp(
            @Value("${datacat.push.credentials-file:}")
            String credentialsFile
    ) throws IOException {

        if (credentialsFile.isBlank()) {
            throw new IllegalStateException(
                    "FCM_ENABLED=true일 때는 "
                            + "FCM_CREDENTIALS_FILE 설정이 필요합니다."
            );
        }

        try (InputStream input = Files.newInputStream(
                Path.of(credentialsFile)
        )) {
            FirebaseOptions options = FirebaseOptions.builder()
                    .setCredentials(
                            GoogleCredentials.fromStream(input)
                    )
                    .build();

            return FirebaseApp.initializeApp(
                    options,
                    "datacat-server"
            );
        }
    }

    @Bean
    public FirebaseMessaging firebaseMessaging(
            FirebaseApp firebaseApp
    ) {
        return FirebaseMessaging.getInstance(firebaseApp);
    }
}