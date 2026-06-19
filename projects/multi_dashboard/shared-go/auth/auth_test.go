package auth_test

import (
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/gofiber/fiber/v2"

	"github.com/mihirzz/chatbot-shared-go/auth"
	apperrors "github.com/mihirzz/chatbot-shared-go/errors"
)

const testSecret = "test-secret-key-please-change-1234"

func TestEncodeDecodeRoundTrip(t *testing.T) {
	tok, err := auth.EncodeJWT(
		map[string]any{"sub": "user-1", "email": "alice@example.com", "role": "admin"},
		testSecret, "HS256", 60, auth.AccessToken,
	)
	if err != nil {
		t.Fatalf("EncodeJWT: %v", err)
	}
	if !strings.Contains(tok, ".") {
		t.Fatalf("token doesn't look like JWT: %q", tok)
	}

	claims, err := auth.VerifyJWT(tok, testSecret, "HS256", auth.AccessToken)
	if err != nil {
		t.Fatalf("VerifyJWT: %v", err)
	}
	if claims.Subject != "user-1" {
		t.Errorf("sub: got %q", claims.Subject)
	}
	if claims.Email != "alice@example.com" {
		t.Errorf("email: got %q", claims.Email)
	}
	if claims.Role != "admin" {
		t.Errorf("role: got %q", claims.Role)
	}
	if claims.Type != auth.AccessToken {
		t.Errorf("type: got %q", claims.Type)
	}
	if claims.JTI == "" {
		t.Error("jti missing")
	}
}

func TestVerifyWrongSecret(t *testing.T) {
	tok, _ := auth.EncodeJWT(
		map[string]any{"sub": "x"},
		"secret-a-1234567890abcdef", "HS256", 60, auth.AccessToken,
	)
	_, err := auth.VerifyJWT(tok, "secret-b-1234567890abcdef", "HS256", auth.AccessToken)
	if err == nil {
		t.Fatal("expected error with wrong secret")
	}
	var ae *apperrors.AppError
	if !errorsAs(err, &ae) {
		t.Fatalf("expected *AppError, got %T", err)
	}
	if ae.Code != "UNAUTHORIZED" {
		t.Errorf("code: got %q", ae.Code)
	}
}

func TestVerifyWrongType(t *testing.T) {
	tok, _ := auth.EncodeJWT(
		map[string]any{"sub": "x"},
		testSecret, "HS256", 60, auth.RefreshToken,
	)
	_, err := auth.VerifyJWT(tok, testSecret, "HS256", auth.AccessToken)
	if err == nil {
		t.Fatal("expected error with wrong token type")
	}

	// But same token with expected type "refresh" works.
	claims, err := auth.VerifyJWT(tok, testSecret, "HS256", auth.RefreshToken)
	if err != nil {
		t.Fatalf("refresh path failed: %v", err)
	}
	if claims.Type != auth.RefreshToken {
		t.Errorf("type: got %q", claims.Type)
	}
}

func TestRequireAuthMiddleware(t *testing.T) {
	app := fiber.New(fiber.Config{ErrorHandler: apperrors.FiberErrorHandler})
	app.Use(auth.RequireAuth(auth.Config{
		SecretProvider: func() string { return testSecret },
	}))
	app.Get("/me", func(c *fiber.Ctx) error {
		claims, err := auth.FromContext(c)
		if err != nil {
			return err
		}
		return c.JSON(fiber.Map{"sub": claims.Subject, "role": claims.Role})
	})

	// 401 without token
	req := httptest.NewRequest("GET", "/me", nil)
	resp, err := app.Test(req)
	if err != nil {
		t.Fatalf("app.Test: %v", err)
	}
	if resp.StatusCode != fiber.StatusUnauthorized {
		t.Errorf("expected 401, got %d", resp.StatusCode)
	}

	// 200 with valid token
	tok, _ := auth.EncodeJWT(map[string]any{"sub": "bob", "role": "user"}, testSecret, "HS256", 60, auth.AccessToken)
	req = httptest.NewRequest("GET", "/me", nil)
	req.Header.Set("Authorization", "Bearer "+tok)
	resp, _ = app.Test(req)
	if resp.StatusCode != fiber.StatusOK {
		t.Errorf("expected 200, got %d", resp.StatusCode)
	}
}

func TestRequireAuthQueryParamFallback(t *testing.T) {
	app := fiber.New(fiber.Config{ErrorHandler: apperrors.FiberErrorHandler})
	app.Use(auth.RequireAuth(auth.Config{
		SecretProvider: func() string { return testSecret },
	}))
	app.Get("/sse", func(c *fiber.Ctx) error { return c.SendStatus(200) })

	tok, _ := auth.EncodeJWT(map[string]any{"sub": "ws-user"}, testSecret, "HS256", 60, auth.AccessToken)
	req := httptest.NewRequest("GET", "/sse?access_token="+tok, nil)
	resp, _ := app.Test(req)
	if resp.StatusCode != fiber.StatusOK {
		t.Errorf("expected 200 from query token, got %d", resp.StatusCode)
	}
}

func TestRequireRole(t *testing.T) {
	app := fiber.New(fiber.Config{ErrorHandler: apperrors.FiberErrorHandler})
	app.Use(auth.RequireAuth(auth.Config{
		SecretProvider: func() string { return testSecret },
	}))
	app.Get("/admin", auth.RequireRole("admin"), func(c *fiber.Ctx) error {
		return c.SendStatus(200)
	})

	userTok, _ := auth.EncodeJWT(map[string]any{"sub": "u", "role": "user"}, testSecret, "HS256", 60, auth.AccessToken)
	adminTok, _ := auth.EncodeJWT(map[string]any{"sub": "a", "role": "admin"}, testSecret, "HS256", 60, auth.AccessToken)

	req := httptest.NewRequest("GET", "/admin", nil)
	req.Header.Set("Authorization", "Bearer "+userTok)
	resp, _ := app.Test(req)
	if resp.StatusCode != fiber.StatusForbidden {
		t.Errorf("user should be 403, got %d", resp.StatusCode)
	}

	req = httptest.NewRequest("GET", "/admin", nil)
	req.Header.Set("Authorization", "Bearer "+adminTok)
	resp, _ = app.Test(req)
	if resp.StatusCode != fiber.StatusOK {
		t.Errorf("admin should be 200, got %d", resp.StatusCode)
	}
}

// errorsAs is a tiny shim to avoid importing the stdlib `errors` package
// (which would shadow our shared-go errors package).
func errorsAs(err error, target any) bool {
	type asser interface{ As(any) bool }
	if e, ok := err.(asser); ok {
		return e.As(target)
	}
	// Fall back to type assertion.
	if t, ok := target.(**apperrors.AppError); ok {
		if e, ok := err.(*apperrors.AppError); ok {
			*t = e
			return true
		}
	}
	return false
}
