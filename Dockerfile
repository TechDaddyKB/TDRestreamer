FROM node:26.7.0-bookworm-slim@sha256:4db36457f406501e6f608802e5da617e5fbd0e80b75901b6a09de1ae5a667d32 AS web
WORKDIR /build/web
COPY web/package*.json ./
RUN npm ci --ignore-scripts
COPY web/ ./
RUN npm run build

FROM golang:1.27.1-bookworm@sha256:69a7b9788769bec032d238959b61854e9ae87f57be9029ec04e9885fabf99195 AS go
WORKDIR /build
COPY go.mod go.sum ./
RUN go mod download
COPY cmd/ cmd/
COPY internal/ internal/
COPY db/ db/
RUN CGO_ENABLED=0 go build -trimpath -o /out/control ./cmd/control && CGO_ENABLED=0 go build -trimpath -o /out/admin ./cmd/admin && CGO_ENABLED=0 go build -trimpath -o /out/worker ./cmd/worker

FROM debian:bookworm-slim@sha256:3783cc01769c7b2b1b83a5c5ad96c815348e28ed7da68e2e3687004faa906251
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates && rm -rf /var/lib/apt/lists/*
ARG VCS_REF=development
LABEL org.opencontainers.image.title="Tech Daddy's Restreamer" org.opencontainers.image.source="https://github.com/camarokris/TDRestreamer" org.opencontainers.image.licenses="AGPL-3.0-or-later" org.opencontainers.image.revision=$VCS_REF
WORKDIR /app
COPY --from=go /out/ ./
COPY --from=web /build/web/dist/ ./web/
COPY LICENSE /app/LICENSE
USER 65532:65532
EXPOSE 8080
CMD ["/app/control"]
