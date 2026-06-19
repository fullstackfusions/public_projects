// Command todo-server is the entry point for the todo-go backend.
//
// Kept thin per refactor-plan §4.2: load Settings, build logger, connect
// pgx pool, run embedded migrations, build Fiber app, mount routes, listen
// with graceful shutdown.
package main

import (
	"context"
	"errors"
	"fmt"
	"log"
	"os/signal"
	"strings"
	"syscall"
	"time"

	"github.com/gofiber/fiber/v2"
	corsmw "github.com/gofiber/fiber/v2/middleware/cors"
	migrate "github.com/golang-migrate/migrate/v4"
	_ "github.com/golang-migrate/migrate/v4/database/pgx/v5"
	"github.com/golang-migrate/migrate/v4/source/iofs"
	"go.uber.org/zap"

	"github.com/mihirzz/chatbot-shared-go/auth"
	shareddb "github.com/mihirzz/chatbot-shared-go/db/sql"
	apperrors "github.com/mihirzz/chatbot-shared-go/errors"
	"github.com/mihirzz/chatbot-shared-go/logging"
	sharedmw "github.com/mihirzz/chatbot-shared-go/middleware"

	"github.com/mihirzz/fullstack_chatbot_llm/backends/todo-go/internal/config"
	"github.com/mihirzz/fullstack_chatbot_llm/backends/todo-go/internal/handlers"
	"github.com/mihirzz/fullstack_chatbot_llm/backends/todo-go/internal/repo"
	"github.com/mihirzz/fullstack_chatbot_llm/backends/todo-go/internal/service"
	"github.com/mihirzz/fullstack_chatbot_llm/backends/todo-go/migrations"
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

	pool, err := shareddb.NewPool(rootCtx, cfg.DatabaseURL)
	if err != nil {
		logger.Fatal("db pool", zap.Error(err))
	}
	defer pool.Close()

	if err := runMigrations(cfg.DatabaseURL, logger); err != nil {
		logger.Fatal("migrations", zap.Error(err))
	}

	todoRepo := repo.NewTodoRepo(pool)
	todoSvc := service.NewTodoService(todoRepo)

	app := fiber.New(fiber.Config{
		AppName:               "todo-backend",
		DisableStartupMessage: true,
		ErrorHandler:          apperrors.FiberErrorHandler,
	})
	sharedmw.Install(app, logger)
	app.Use(corsmw.New(corsmw.Config{
		AllowOrigins:     strings.Join(cfg.CORSOrigins, ","),
		AllowMethods:     "GET,POST,PUT,PATCH,DELETE,OPTIONS",
		AllowHeaders:     "Authorization,Content-Type,X-Request-ID",
		AllowCredentials: len(cfg.CORSOrigins) > 0,
	}))

	handlers.RegisterHealth(app, pool)
	handlers.RegisterTodos(app, todoSvc, auth.RequireAuth(auth.Config{
		SecretProvider: func() string { return cfg.AuthSecretKey },
		Algorithm:      cfg.AuthAlgorithm,
	}))

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

// runMigrations applies all pending up-migrations from the embedded FS.
// ErrNoChange is treated as success — idempotent on re-runs.
func runMigrations(dbURL string, logger *zap.Logger) error {
	src, err := iofs.New(migrations.FS, ".")
	if err != nil {
		return fmt.Errorf("iofs source: %w", err)
	}

	migrateURL := toMigrateURL(dbURL)
	m, err := migrate.NewWithSourceInstance("iofs", src, migrateURL)
	if err != nil {
		return fmt.Errorf("migrate init: %w", err)
	}
	defer func() {
		if srcErr, dbErr := m.Close(); srcErr != nil || dbErr != nil {
			logger.Warn("migrate close",
				zap.NamedError("src", srcErr),
				zap.NamedError("db", dbErr))
		}
	}()

	if err := m.Up(); err != nil && !errors.Is(err, migrate.ErrNoChange) {
		return fmt.Errorf("migrate up: %w", err)
	}
	logger.Info("migrations applied")
	return nil
}

// toMigrateURL converts a libpq URL into the form the pgx5 migrate driver
// expects: `pgx5://user:pass@host:port/db?...`.
func toMigrateURL(dbURL string) string {
	for _, prefix := range []string{"postgres://", "postgresql://"} {
		if strings.HasPrefix(dbURL, prefix) {
			return "pgx5://" + strings.TrimPrefix(dbURL, prefix)
		}
	}
	return dbURL
}
