package errors_test

import (
	"encoding/json"
	"io"
	"net/http/httptest"
	"testing"

	"github.com/gofiber/fiber/v2"

	apperrors "github.com/mihirzz/chatbot-shared-go/errors"
)

func TestNotFoundEnvelope(t *testing.T) {
	app := fiber.New(fiber.Config{ErrorHandler: apperrors.FiberErrorHandler})
	app.Get("/x", func(c *fiber.Ctx) error {
		return apperrors.NewNotFound("thing missing", map[string]any{"id": "abc"})
	})

	resp, err := app.Test(httptest.NewRequest("GET", "/x", nil))
	if err != nil {
		t.Fatal(err)
	}
	if resp.StatusCode != fiber.StatusNotFound {
		t.Errorf("status: got %d", resp.StatusCode)
	}

	body, _ := io.ReadAll(resp.Body)
	var env apperrors.ErrorEnvelope
	if err := json.Unmarshal(body, &env); err != nil {
		t.Fatalf("unmarshal: %v body=%s", err, body)
	}
	if env.Code != "NOT_FOUND" {
		t.Errorf("code: got %q", env.Code)
	}
	if env.Message != "thing missing" {
		t.Errorf("message: got %q", env.Message)
	}
	if env.Detail["id"] != "abc" {
		t.Errorf("detail: got %v", env.Detail)
	}
}

func TestUnknownErrorReturns500(t *testing.T) {
	app := fiber.New(fiber.Config{ErrorHandler: apperrors.FiberErrorHandler})
	app.Get("/boom", func(c *fiber.Ctx) error {
		return io.ErrUnexpectedEOF // plain error -> 500 envelope
	})

	resp, _ := app.Test(httptest.NewRequest("GET", "/boom", nil))
	if resp.StatusCode != fiber.StatusInternalServerError {
		t.Errorf("expected 500, got %d", resp.StatusCode)
	}
}
