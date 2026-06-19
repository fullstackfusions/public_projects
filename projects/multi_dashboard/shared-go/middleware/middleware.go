// Package middleware bundles Fiber middleware: request id, access log, recover.
//
// Install in one call:
//
//	middleware.Install(app, logger)
package middleware

import (
	"time"

	"github.com/gofiber/fiber/v2"
	"github.com/google/uuid"
	"go.uber.org/zap"
)

const (
	RequestIDHeader = "X-Request-ID"
	RequestIDKey    = "request_id"
)

// RequestID echoes inbound X-Request-ID or generates a UUID. Stored on the
// Fiber context locals so other middleware and handlers can correlate logs.
func RequestID() fiber.Handler {
	return func(c *fiber.Ctx) error {
		rid := c.Get(RequestIDHeader)
		if rid == "" {
			rid = uuid.NewString()
		}
		c.Locals(RequestIDKey, rid)
		c.Set(RequestIDHeader, rid)
		return c.Next()
	}
}

// AccessLog emits one JSON log line per request.
func AccessLog(logger *zap.Logger) fiber.Handler {
	return func(c *fiber.Ctx) error {
		start := time.Now()
		err := c.Next()
		duration := time.Since(start)

		rid, _ := c.Locals(RequestIDKey).(string)
		fields := []zap.Field{
			zap.String("request_id", rid),
			zap.String("method", c.Method()),
			zap.String("path", c.Path()),
			zap.Int("status_code", c.Response().StatusCode()),
			zap.Float64("duration_ms", float64(duration.Microseconds())/1000.0),
		}
		if err != nil {
			fields = append(fields, zap.Error(err))
			logger.Warn("request", fields...)
		} else {
			logger.Info("request", fields...)
		}
		return err
	}
}

// Recover catches panics and converts them into a 500 envelope via the
// configured ErrorHandler.
func Recover() fiber.Handler {
	return func(c *fiber.Ctx) (err error) {
		defer func() {
			if r := recover(); r != nil {
				err = fiber.NewError(fiber.StatusInternalServerError, "panic recovered")
			}
		}()
		return c.Next()
	}
}

// Install wires RequestID -> Recover -> AccessLog in the recommended order.
func Install(app *fiber.App, logger *zap.Logger) {
	app.Use(RequestID())
	app.Use(Recover())
	app.Use(AccessLog(logger))
}
