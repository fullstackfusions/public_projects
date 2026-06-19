// Package errors mirrors shared-py's error envelope so the frontend sees the
// same JSON shape regardless of which backend produced the response.
//
//	{
//	    "code": "NOT_FOUND",
//	    "message": "Thing missing",
//	    "detail": {"id": "abc"},
//	    "trace_id": "request-id-here"
//	}
package errors

import (
	"errors"

	"github.com/gofiber/fiber/v2"
)

// ErrorEnvelope is the wire shape.
type ErrorEnvelope struct {
	Code    string         `json:"code"`
	Message string         `json:"message"`
	Detail  map[string]any `json:"detail,omitempty"`
	TraceID string         `json:"trace_id,omitempty"`
}

// AppError is a structured application error. Wrapping it via `errors.As`
// lets handlers know what status to return.
type AppError struct {
	Code       string
	Message    string
	StatusCode int
	Detail     map[string]any
}

func (e *AppError) Error() string { return e.Message }

// Constructors mirror the Python subclasses.
func NewNotFound(msg string, detail map[string]any) *AppError {
	return &AppError{Code: "NOT_FOUND", Message: msg, StatusCode: fiber.StatusNotFound, Detail: detail}
}

func NewConflict(msg string, detail map[string]any) *AppError {
	return &AppError{Code: "CONFLICT", Message: msg, StatusCode: fiber.StatusConflict, Detail: detail}
}

func NewValidation(msg string, detail map[string]any) *AppError {
	return &AppError{Code: "VALIDATION_ERROR", Message: msg, StatusCode: 422, Detail: detail}
}

func NewUnauthorized(msg string, detail map[string]any) *AppError {
	return &AppError{Code: "UNAUTHORIZED", Message: msg, StatusCode: fiber.StatusUnauthorized, Detail: detail}
}

func NewForbidden(msg string, detail map[string]any) *AppError {
	return &AppError{Code: "FORBIDDEN", Message: msg, StatusCode: fiber.StatusForbidden, Detail: detail}
}

func NewBadGateway(msg string, detail map[string]any) *AppError {
	return &AppError{Code: "BAD_GATEWAY", Message: msg, StatusCode: fiber.StatusBadGateway, Detail: detail}
}

func NewInternal(msg string, detail map[string]any) *AppError {
	return &AppError{Code: "INTERNAL_ERROR", Message: msg, StatusCode: fiber.StatusInternalServerError, Detail: detail}
}

// WriteError renders any error as an ErrorEnvelope response. AppError values
// keep their code/status; everything else degrades to a generic 500.
//
// `traceID` comes from c.Locals("request_id") set by the RequestID
// middleware.
func WriteError(c *fiber.Ctx, err error) error {
	traceID, _ := c.Locals("request_id").(string)

	var ae *AppError
	if errors.As(err, &ae) {
		return c.Status(ae.StatusCode).JSON(ErrorEnvelope{
			Code:    ae.Code,
			Message: ae.Message,
			Detail:  ae.Detail,
			TraceID: traceID,
		})
	}

	// fiber.Error preserves HTTP status the framework wants to use.
	var fe *fiber.Error
	if errors.As(err, &fe) {
		return c.Status(fe.Code).JSON(ErrorEnvelope{
			Code:    "HTTP_ERROR",
			Message: fe.Message,
			TraceID: traceID,
		})
	}

	return c.Status(fiber.StatusInternalServerError).JSON(ErrorEnvelope{
		Code:    "INTERNAL_ERROR",
		Message: "Internal server error",
		TraceID: traceID,
	})
}

// FiberErrorHandler is the canonical app-wide handler. Wire it via:
//
//	app := fiber.New(fiber.Config{ErrorHandler: errors.FiberErrorHandler})
func FiberErrorHandler(c *fiber.Ctx, err error) error {
	return WriteError(c, err)
}
