package com.datacat.server.push;

import org.springframework.data.jpa.repository.JpaRepository;

public interface PushTokenRepository
        extends JpaRepository<PushToken, String> {
}