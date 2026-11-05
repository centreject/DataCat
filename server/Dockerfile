FROM eclipse-temurin:21-jdk-jammy AS build
WORKDIR /src
COPY gradlew build.gradle settings.gradle ./
COPY gradle ./gradle
COPY src/main ./src/main
RUN sed -i 's/\r$//' gradlew && chmod +x gradlew \
    && ./gradlew --no-daemon bootJar -x test \
    && find build/libs -maxdepth 1 -type f -name '*.jar' ! -name '*-plain.jar' -exec cp {} /tmp/server.jar \; \
    && test -s /tmp/server.jar

FROM eclipse-temurin:21-jre-jammy
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 10001 app && useradd --uid 10001 --gid app --create-home app \
    && mkdir -p /app /data/snapshots && chown -R app:app /app /data/snapshots
WORKDIR /app
COPY --from=build --chown=app:app /tmp/server.jar /app/server.jar
USER app
EXPOSE 8080
HEALTHCHECK --interval=10s --timeout=5s --start-period=60s --retries=12 \
    CMD curl --fail --silent --show-error --max-time 3 --output /dev/null 'http://localhost:8080/api/v1/events?page=0&size=1' || exit 1
ENTRYPOINT ["java", "-jar", "/app/server.jar"]
