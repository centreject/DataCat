package com.datacat.server.device;

import org.springframework.data.jpa.repository.JpaRepository;

public interface DevicePackageStateRepository
        extends JpaRepository<DevicePackageState, String> {
}