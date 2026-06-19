package middleware_test

import (
	"net/http/httptest"
	"testing"

	"github.com/gofiber/fiber/v2"
	"go.uber.org/zap"

	"github.com/mihirzz/chatbot-shared-go/middleware"
)

func TestRequestIDGeneratedAndEchoed(t *testing.T) {
	app := fiber.New()
	app.Use(middleware.RequestID())
	app.Get("/", func(c *fiber.Ctx) error {
		rid, _ := c.Locals(middleware.RequestIDKey).(string)
		if rid == "" {
			return fiber.NewError(500, "missing rid in locals")
		}
		return c.SendString(rid)
	})

	resp, err := app.Test(httptest.NewRequest("GET", "/", nil))
	if err != nil {
		t.Fatal(err)
	}
	if resp.StatusCode != 200 {
		t.Errorf("status: %d", resp.StatusCode)
	}
	if resp.Header.Get(middleware.RequestIDHeader) == "" {
		t.Error("X-Request-ID header missing")
	}
}

func TestRequestIDEchoesInbound(t *testing.T) {
	app := fiber.New()
	app.Use(middleware.RequestID())
	app.Get("/", func(c *fiber.Ctx) error { return c.SendStatus(204) })

	req := httptest.NewRequest("GET", "/", nil)
	req.Header.Set("X-Request-ID", "abc-123")
	resp, _ := app.Test(req)
	if got := resp.Header.Get("X-Request-ID"); got != "abc-123" {
		t.Errorf("expected abc-123, got %q", got)
	}
}

func TestAccessLogDoesNotPanic(t *testing.T) {
	app := fiber.New()
	app.Use(middleware.RequestID())
	app.Use(middleware.AccessLog(zap.NewNop()))
	app.Get("/", func(c *fiber.Ctx) error { return c.SendStatus(200) })

	resp, _ := app.Test(httptest.NewRequest("GET", "/", nil))
	if resp.StatusCode != 200 {
		t.Errorf("status: %d", resp.StatusCode)
	}
}
