// Package testing provides Fiber-flavored helpers for service tests.
//
// Don't confuse with the stdlib "testing" package — import as `sharedtest`:
//
//	import sharedtest "github.com/mihirzz/chatbot-shared-go/testing"
package testing

import (
	"github.com/gofiber/fiber/v2"

	"github.com/mihirzz/chatbot-shared-go/auth"
	apperrors "github.com/mihirzz/chatbot-shared-go/errors"
)

// NewTestApp returns a fresh Fiber app with the canonical error handler
// already wired so tests see the same envelope shape as production.
func NewTestApp() *fiber.App {
	return fiber.New(fiber.Config{
		ErrorHandler: apperrors.FiberErrorHandler,
		DisableStartupMessage: true,
	})
}

// MintTestToken creates an access token signed with `secret` carrying `sub`
// and `role`. Use to authenticate requests in integration tests.
func MintTestToken(sub, role, secret string) (string, error) {
	return auth.EncodeJWT(
		map[string]any{"sub": sub, "role": role, "email": sub + "@test.local"},
		secret,
		"HS256",
		3600,
		auth.AccessToken,
	)
}

// AuthHeader returns a Bearer header for the given token, ready to pass to
// httptest.NewRequest or Fiber's Test().
func AuthHeader(token string) map[string]string {
	return map[string]string{fiber.HeaderAuthorization: "Bearer " + token}
}
