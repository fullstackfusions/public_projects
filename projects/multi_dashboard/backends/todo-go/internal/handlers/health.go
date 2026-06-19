// Package handlers exposes Fiber HTTP handlers.
package handlers

import (
	"context"
	"time"

	"github.com/gofiber/fiber/v2"
	"github.com/jackc/pgx/v5/pgxpool"
)

// RegisterHealth mounts the public liveness + readiness probes.
//
//   - GET /health  → 200 always (process liveness)
//   - GET /ready   → 200 when DB reachable, 503 otherwise
func RegisterHealth(app *fiber.App, pool *pgxpool.Pool) {
	app.Get("/health", func(c *fiber.Ctx) error {
		return c.JSON(fiber.Map{"status": "ok"})
	})

	app.Get("/ready", func(c *fiber.Ctx) error {
		ctx, cancel := context.WithTimeout(c.UserContext(), 2*time.Second)
		defer cancel()
		if err := pool.Ping(ctx); err != nil {
			return c.Status(fiber.StatusServiceUnavailable).
				JSON(fiber.Map{"status": "unavailable", "detail": err.Error()})
		}
		return c.JSON(fiber.Map{"status": "ok"})
	})
}
