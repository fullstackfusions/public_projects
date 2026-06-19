// Package auth provides local HS256 JWT helpers + a Fiber middleware.
//
// Tokens are interoperable with shared-py: same `sub`/`email`/`role`/`type`/
// `iat`/`exp`/`jti` claims, same HS256 algorithm, same shared secret. A token
// issued by auth-py decodes here and vice versa.
package auth

import (
	stderrors "errors"
	"fmt"
	"strings"
	"time"

	"github.com/gofiber/fiber/v2"
	"github.com/golang-jwt/jwt/v5"
	"github.com/google/uuid"

	apperrors "github.com/mihirzz/chatbot-shared-go/errors"
)

// TokenType matches shared-py.
type TokenType string

const (
	AccessToken  TokenType = "access"
	RefreshToken TokenType = "refresh"
)

// Claims is the decoded payload. Fields match shared-py TokenClaims so a
// frontend or third service can rely on the same shape.
type Claims struct {
	Subject string    `json:"sub"`
	Email   string    `json:"email,omitempty"`
	Name    string    `json:"name,omitempty"`
	Role    string    `json:"role"`
	Type    TokenType `json:"type"`
	JTI     string    `json:"jti"`

	jwt.RegisteredClaims
}

// EncodeJWT mints a token using HS256. `payload` may include `sub`, `email`,
// `name`, `role`. Standard claims (`iat`, `exp`, `jti`, `type`) are filled in.
func EncodeJWT(
	payload map[string]any,
	secret string,
	algorithm string,
	expiresInSeconds int64,
	tokenType TokenType,
) (string, error) {
	if algorithm != "HS256" {
		return "", fmt.Errorf("only HS256 supported, got %q", algorithm)
	}

	now := time.Now().UTC()
	jti, _ := payload["jti"].(string)
	if jti == "" {
		jti = uuid.NewString()
	}

	claims := jwt.MapClaims{
		"iat":  now.Unix(),
		"exp":  now.Add(time.Duration(expiresInSeconds) * time.Second).Unix(),
		"jti":  jti,
		"type": string(tokenType),
	}
	for k, v := range payload {
		if v == nil {
			continue
		}
		claims[k] = v
	}
	// Required fields with sensible defaults
	if _, ok := claims["role"]; !ok {
		claims["role"] = "user"
	}

	tok := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
	return tok.SignedString([]byte(secret))
}

// VerifyJWT decodes and validates a token. Returns an *apperrors.AppError
// (UNAUTHORIZED) on any failure so the Fiber error handler can render the
// standard envelope.
//
// `expectedType` may be "" to skip the type check.
func VerifyJWT(token, secret, algorithm string, expectedType TokenType) (*Claims, error) {
	if algorithm == "" {
		algorithm = "HS256"
	}
	if algorithm != "HS256" {
		return nil, apperrors.NewUnauthorized("Unsupported algorithm", map[string]any{"algorithm": algorithm})
	}

	parsed, err := jwt.Parse(token, func(t *jwt.Token) (any, error) {
		if t.Method.Alg() != algorithm {
			return nil, fmt.Errorf("unexpected signing method: %s", t.Method.Alg())
		}
		return []byte(secret), nil
	})
	if err != nil {
		return nil, apperrors.NewUnauthorized("Invalid or expired token", map[string]any{"reason": err.Error()})
	}
	if !parsed.Valid {
		return nil, apperrors.NewUnauthorized("Invalid token", nil)
	}

	mc, ok := parsed.Claims.(jwt.MapClaims)
	if !ok {
		return nil, apperrors.NewUnauthorized("Malformed claims", nil)
	}

	claims := &Claims{Role: "user", Type: AccessToken}
	if v, ok := mc["sub"].(string); ok {
		claims.Subject = v
	}
	if v, ok := mc["email"].(string); ok {
		claims.Email = v
	}
	if v, ok := mc["name"].(string); ok {
		claims.Name = v
	}
	if v, ok := mc["role"].(string); ok {
		claims.Role = v
	}
	if v, ok := mc["type"].(string); ok {
		claims.Type = TokenType(v)
	}
	if v, ok := mc["jti"].(string); ok {
		claims.JTI = v
	}
	if v, ok := mc["exp"].(float64); ok {
		claims.ExpiresAt = jwt.NewNumericDate(time.Unix(int64(v), 0))
	}
	if v, ok := mc["iat"].(float64); ok {
		claims.IssuedAt = jwt.NewNumericDate(time.Unix(int64(v), 0))
	}

	if expectedType != "" && claims.Type != expectedType {
		return nil, apperrors.NewUnauthorized("Wrong token type", map[string]any{
			"expected": expectedType, "got": claims.Type,
		})
	}
	return claims, nil
}

// ---------------------------------------------------------------------------
// Fiber middleware
// ---------------------------------------------------------------------------

// Config configures RequireAuth.
type Config struct {
	// SecretProvider returns the current shared secret. Wrapped in a function
	// so tests/hot-reloads can swap it.
	SecretProvider func() string
	// Algorithm defaults to "HS256".
	Algorithm string
	// ExpectedType defaults to AccessToken.
	ExpectedType TokenType
	// QueryParamName allows ?access_token=... fallback for SSE/WS. Default "access_token".
	QueryParamName string
}

// LocalsKey is the Fiber context key where verified claims are stored.
const LocalsKey = "auth_claims"

// RequireAuth builds a Fiber middleware that decodes a Bearer token and
// stores the claims on the request context. Missing or invalid tokens return
// an UNAUTHORIZED envelope.
func RequireAuth(cfg Config) fiber.Handler {
	if cfg.SecretProvider == nil {
		panic("auth.RequireAuth: SecretProvider is required")
	}
	if cfg.Algorithm == "" {
		cfg.Algorithm = "HS256"
	}
	if cfg.ExpectedType == "" {
		cfg.ExpectedType = AccessToken
	}
	if cfg.QueryParamName == "" {
		cfg.QueryParamName = "access_token"
	}

	return func(c *fiber.Ctx) error {
		token := extractToken(c, cfg.QueryParamName)
		if token == "" {
			return apperrors.NewUnauthorized("Missing bearer token", nil)
		}
		claims, err := VerifyJWT(token, cfg.SecretProvider(), cfg.Algorithm, cfg.ExpectedType)
		if err != nil {
			return err
		}
		c.Locals(LocalsKey, claims)
		return c.Next()
	}
}

// FromContext retrieves the verified claims set by RequireAuth.
func FromContext(c *fiber.Ctx) (*Claims, error) {
	v := c.Locals(LocalsKey)
	if v == nil {
		return nil, stderrors.New("auth.FromContext: no claims in context (was RequireAuth installed?)")
	}
	claims, ok := v.(*Claims)
	if !ok {
		return nil, stderrors.New("auth.FromContext: unexpected claims type")
	}
	return claims, nil
}

// RequireRole builds a Fiber handler that 403s if the user lacks one of the
// allowed roles. Chain after RequireAuth.
func RequireRole(allowed ...string) fiber.Handler {
	return func(c *fiber.Ctx) error {
		claims, err := FromContext(c)
		if err != nil {
			return apperrors.NewUnauthorized(err.Error(), nil)
		}
		for _, r := range allowed {
			if claims.Role == r {
				return c.Next()
			}
		}
		return apperrors.NewForbidden("Insufficient role", map[string]any{
			"required": allowed, "got": claims.Role,
		})
	}
}

func extractToken(c *fiber.Ctx, queryParam string) string {
	if auth := c.Get(fiber.HeaderAuthorization); auth != "" {
		const prefix = "Bearer "
		if strings.HasPrefix(auth, prefix) {
			return strings.TrimSpace(auth[len(prefix):])
		}
	}
	return c.Query(queryParam)
}
