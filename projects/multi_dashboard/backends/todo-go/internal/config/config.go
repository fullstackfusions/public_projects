// Package config defines the todo-go Settings struct and loader.
package config

import (
	"errors"
	"fmt"

	sharedconfig "github.com/mihirzz/chatbot-shared-go/config"
)

// Settings extends shared BaseSettings with todo-specific fields.
type Settings struct {
	sharedconfig.BaseSettings `mapstructure:",squash"`

	Port        string `mapstructure:"port"`
	DatabaseURL string `mapstructure:"database_url"`
}

// Load reads environment + optional .env and returns a validated Settings.
func Load() (Settings, error) {
	cfg, err := sharedconfig.LoadConfig[Settings]("todo-backend")
	if err != nil {
		return cfg, fmt.Errorf("load config: %w", err)
	}
	if err := cfg.Validate(); err != nil {
		return cfg, fmt.Errorf("invalid config: %w", err)
	}
	return cfg, nil
}

// Validate fails fast on missing required fields.
func (s Settings) Validate() error {
	if err := s.BaseSettings.Validate(); err != nil {
		return err
	}
	if s.DatabaseURL == "" {
		return errors.New("DATABASE_URL is required")
	}
	if s.Port == "" {
		return errors.New("PORT is required")
	}
	return nil
}
