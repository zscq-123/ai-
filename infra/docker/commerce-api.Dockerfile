FROM eclipse-temurin:25-jdk AS build
WORKDIR /workspace
COPY services/commerce-api services/commerce-api
RUN cd services/commerce-api && ./mvnw -B -DskipTests package

FROM eclipse-temurin:25-jre
RUN useradd --system --uid 10001 commerce
WORKDIR /app
COPY --from=build /workspace/services/commerce-api/target/commerce-api-*.jar app.jar
USER commerce
EXPOSE 8080
ENTRYPOINT ["java", "-XX:MaxRAMPercentage=75", "-jar", "/app/app.jar"]
