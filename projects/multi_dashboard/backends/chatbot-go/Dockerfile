# Build context: repo root (so we can COPY shared-go alongside the service).
#
#   docker build -f backends/chatbot-go/Dockerfile .
FROM golang:1.22-alpine AS builder

RUN apk add --no-cache git

WORKDIR /workspace

# shared-go must exist at the path go.mod's `replace` directive expects.
COPY shared-go ./shared-go
COPY backends/chatbot-go ./backends/chatbot-go

WORKDIR /workspace/backends/chatbot-go

RUN go mod download
RUN CGO_ENABLED=0 GOOS=linux go build -trimpath -ldflags="-s -w" -o /out/chatbot-api ./cmd/server

# Alpine runtime: ca-certificates for outbound TLS, wget for healthchecks.
FROM alpine:3.20

RUN apk add --no-cache ca-certificates wget

COPY --from=builder /out/chatbot-api /usr/local/bin/chatbot-api

ENV PORT=8004
EXPOSE 8004

ENTRYPOINT ["/usr/local/bin/chatbot-api"]
