# Build context: repo root (so we can COPY shared-go alongside the service).
#
#   docker build -f backends/todo-go/Dockerfile .
FROM golang:1.22-alpine AS builder

RUN apk add --no-cache git

WORKDIR /workspace

# shared-go must exist at the path go.mod's `replace` directive expects.
COPY shared-go ./shared-go
COPY backends/todo-go ./backends/todo-go

WORKDIR /workspace/backends/todo-go

RUN go mod download
RUN CGO_ENABLED=0 GOOS=linux go build -trimpath -ldflags="-s -w" -o /out/todo-api ./cmd/server

# Alpine runtime: ca-certificates for outbound TLS, wget for healthchecks.
FROM alpine:3.20

RUN apk add --no-cache ca-certificates wget

COPY --from=builder /out/todo-api /usr/local/bin/todo-api

ENV PORT=8080
EXPOSE 8080

ENTRYPOINT ["/usr/local/bin/todo-api"]
