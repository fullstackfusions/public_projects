// Package handlers exposes Fiber HTTP handlers for chatbot-go.
package handlers

import (
	"github.com/gofiber/fiber/v2"
)

// RegisterHealth mounts the public liveness + readiness probes.
//
//   - GET /health → 200 always
//   - GET /ready  → 200 always (no DB dependency)
func RegisterHealth(app *fiber.App) {
	app.Get("/health", func(c *fiber.Ctx) error {
		return c.JSON(fiber.Map{"status": "ok"})
	})
	app.Get("/ready", func(c *fiber.Ctx) error {
		return c.JSON(fiber.Map{"status": "ok"})
	})
}
