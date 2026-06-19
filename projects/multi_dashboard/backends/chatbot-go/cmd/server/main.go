// Command chatbot-server is the entry point for chatbot-go.
//
// Kept thin per refactor-plan §4.2: load Settings, build logger, wire Fiber
// app, mount routes, listen with graceful SIGTERM shutdown.
package main

import (
	"context"
	"log"
	"os/signal"
	"strings"
	"syscall"
	"time"

	"github.com/gofiber/fiber/v2"
	corsmw "github.com/gofiber/fiber/v2/middleware/cors"
	"go.uber.org/zap"

	"github.com/mihirzz/chatbot-shared-go/auth"
	apperrors "github.com/mihirzz/chatbot-shared-go/errors"
	"github.com/mihirzz/chatbot-shared-go/logging"
	sharedmw "github.com/mihirzz/chatbot-shared-go/middleware"

	"github.com/mihirzz/fullstack_chatbot_llm/backends/chatbot-go/internal/config"
	"github.com/mihirzz/fullstack_chatbot_llm/backends/chatbot-go/internal/handlers"
	"github.com/mihirzz/fullstack_chatbot_llm/backends/chatbot-go/internal/store"
)

func main() {
	cfg, err := config.Load()
	if err != nil {
		log.Fatalf("config: %v", err)
	}

	logger, err := logging.NewLogger(cfg.ServiceName, cfg.LogLevel)
	if err != nil {
		log.Fatalf("logger: %v", err)
	}
	defer func() { _ = logger.Sync() }()

	rootCtx, cancel := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer cancel()

	chatStore := store.New()

	authMw := auth.RequireAuth(auth.Config{
		SecretProvider: func() string { return cfg.AuthSecretKey },
		Algorithm:      cfg.AuthAlgorithm,
	})

	app := fiber.New(fiber.Config{
		AppName:               "chatbot-go",
		DisableStartupMessage: true,
		ErrorHandler:          apperrors.FiberErrorHandler,
	})
	sharedmw.Install(app, logger)
	app.Use(corsmw.New(corsmw.Config{
		AllowOrigins:     strings.Join(cfg.CORSOrigins, ","),
		AllowMethods:     "GET,POST,DELETE,OPTIONS",
		AllowHeaders:     "Authorization,Content-Type,X-Request-ID",
		AllowCredentials: len(cfg.CORSOrigins) > 0,
	}))

	handlers.RegisterHealth(app)
	handlers.RegisterWS(app, chatStore, authMw)
	handlers.RegisterChat(app, chatStore, authMw)

	addr := ":" + cfg.Port
	logger.Info("starting", zap.String("addr", addr))

	listenErr := make(chan error, 1)
	go func() {
		if err := app.Listen(addr); err != nil {
			listenErr <- err
		}
	}()

	select {
	case <-rootCtx.Done():
		logger.Info("shutdown signal received")
	case err := <-listenErr:
		logger.Fatal("listen failed", zap.Error(err))
	}

	shutdownCtx, scancel := context.WithTimeout(context.Background(), 15*time.Second)
	defer scancel()
	if err := app.ShutdownWithContext(shutdownCtx); err != nil {
		logger.Error("shutdown", zap.Error(err))
	}
}
