FROM mcr.microsoft.com/dotnet/core/aspnet:3.1 AS base
WORKDIR /app
EXPOSE 80

FROM mcr.microsoft.com/dotnet/core/sdk:3.1 AS publish
WORKDIR /src
COPY /src .
WORKDIR "/src/Server"
RUN dotnet publish "Server.csproj" -c Release -o /app/publish

FROM base AS final
WORKDIR /app
COPY --from=publish /app/publish .
VOLUME ["/app/logs"]
HEALTHCHECK --interval=15s --timeout=3s CMD curl --fail --silent http://localhost/health || exit 1
ENTRYPOINT ["dotnet", "Server.dll"]

ARG BUILD_DATE
ARG VCS_REF
ARG BUILD_VERSION
LABEL org.label-schema.schema-version="1.0"
LABEL org.label-schema.build-date=$BUILD_DATE
LABEL org.label-schema.name="gRPC Server"
LABEL org.label-schema.description="A gRPC server project"
LABEL org.label-schema.vendor="AntSoft"
LABEL org.label-schema.vcs-ref=$VCS_REF
LABEL org.label-schema.version=$BUILD_VERSION
LABEL org.label-schema.vcs-url=https://github.com/antsoftxyz/DevOps.git