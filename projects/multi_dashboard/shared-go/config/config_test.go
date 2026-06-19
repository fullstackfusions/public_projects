package config_test

import (
	"testing"

	"github.com/mihirzz/chatbot-shared-go/config"
)

type testCfg struct {
	config.BaseSettings `mapstructure:",squash"`
	ExtraKey            string `mapstructure:"extra_key"`
}

func TestLoadConfigFromEnv(t *testing.T) {
	t.Setenv("SERVICE_NAME", "demo-svc")
	t.Setenv("AUTH_SECRET_KEY", "test-secret-1234567890abcdef")
	t.Setenv("ENVIRONMENT", "test")
	t.Setenv("LOG_LEVEL", "debug")
	t.Setenv("EXTRA_KEY", "hello")

	cfg, err := config.LoadConfig[testCfg]("fallback-name")
	if err != nil {
		t.Fatalf("LoadConfig: %v", err)
	}
	if cfg.ServiceName != "demo-svc" {
		t.Errorf("service_name: got %q", cfg.ServiceName)
	}
	if cfg.Environment != "test" {
		t.Errorf("environment: got %q", cfg.Environment)
	}
	if cfg.LogLevel != "debug" {
		t.Errorf("log_level: got %q", cfg.LogLevel)
	}
	if cfg.AuthSecretKey != "test-secret-1234567890abcdef" {
		t.Errorf("auth_secret_key wrong")
	}
	if cfg.ExtraKey != "hello" {
		t.Errorf("extra_key: got %q", cfg.ExtraKey)
	}
	if err := cfg.BaseSettings.Validate(); err != nil {
		t.Errorf("Validate: %v", err)
	}
}

func TestCORSOriginsParsing(t *testing.T) {
	t.Setenv("SERVICE_NAME", "demo")
	t.Setenv("AUTH_SECRET_KEY", "test-secret-1234567890abcdef")
	t.Setenv("CORS_ORIGINS", "http://localhost:5173, https://app.example.com")

	cfg, err := config.LoadConfig[testCfg]("demo")
	if err != nil {
		t.Fatal(err)
	}
	if len(cfg.CORSOrigins) != 2 {
		t.Fatalf("expected 2 origins, got %d (%v)", len(cfg.CORSOrigins), cfg.CORSOrigins)
	}
	if cfg.CORSOrigins[0] != "http://localhost:5173" {
		t.Errorf("origin[0]: %q", cfg.CORSOrigins[0])
	}
}

func TestValidateRejectsShortSecret(t *testing.T) {
	b := config.BaseSettings{ServiceName: "x", AuthSecretKey: "short"}
	if err := b.Validate(); err == nil {
		t.Error("expected error on short secret")
	}
}
