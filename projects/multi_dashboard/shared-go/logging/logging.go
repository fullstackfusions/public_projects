// Package logging provides a zap-based structured JSON logger factory.
//
// Every log line includes service name + level + timestamp. When called from
// inside a Fiber handler, the request id can be retrieved from the context
// and added via `.With(zap.String("request_id", rid))`.
package logging

import (
	"strings"

	"go.uber.org/zap"
	"go.uber.org/zap/zapcore"
)

// NewLogger returns a JSON logger keyed to the given service name.
// `levelStr` is "debug" | "info" | "warn" | "error" (case-insensitive).
func NewLogger(serviceName, levelStr string) (*zap.Logger, error) {
	level := parseLevel(levelStr)

	encoderCfg := zap.NewProductionEncoderConfig()
	encoderCfg.TimeKey = "timestamp"
	encoderCfg.LevelKey = "level"
	encoderCfg.MessageKey = "message"
	encoderCfg.EncodeTime = zapcore.ISO8601TimeEncoder

	cfg := zap.Config{
		Level:             zap.NewAtomicLevelAt(level),
		Encoding:          "json",
		EncoderConfig:     encoderCfg,
		OutputPaths:       []string{"stdout"},
		ErrorOutputPaths:  []string{"stderr"},
		DisableStacktrace: false,
		InitialFields:     map[string]any{"service": serviceName},
	}
	return cfg.Build()
}

func parseLevel(s string) zapcore.Level {
	switch strings.ToLower(s) {
	case "debug":
		return zapcore.DebugLevel
	case "warn", "warning":
		return zapcore.WarnLevel
	case "error":
		return zapcore.ErrorLevel
	default:
		return zapcore.InfoLevel
	}
}
