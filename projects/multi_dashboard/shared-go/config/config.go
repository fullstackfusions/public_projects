// Package config provides a viper-backed configuration loader.
//
// Services declare a struct with `mapstructure` tags and pass it to
// LoadConfig. Env vars take precedence over an optional .env file.
//
//	type TodoSettings struct {
//	    config.BaseSettings `mapstructure:",squash"`
//	    DatabaseURL string `mapstructure:"todo_database_url"`
//	}
//
//	cfg, err := config.LoadConfig[TodoSettings]("todo-go")
//	if err != nil { log.Fatal(err) }
package config

import (
	"errors"
	"fmt"
	"reflect"
	"strings"

	"github.com/spf13/viper"
)

// BaseSettings holds keys every service shares.
// Embed via `mapstructure:",squash"`.
type BaseSettings struct {
	ServiceName              string   `mapstructure:"service_name"`
	Environment              string   `mapstructure:"environment"`
	LogLevel                 string   `mapstructure:"log_level"`
	CORSOrigins              []string `mapstructure:"cors_origins"`
	AuthSecretKey            string   `mapstructure:"auth_secret_key"`
	AuthAlgorithm            string   `mapstructure:"auth_algorithm"`
	AccessTokenExpireMinutes int      `mapstructure:"access_token_expire_minutes"`
	RefreshTokenExpireDays   int      `mapstructure:"refresh_token_expire_days"`
}

// LoadConfig reads .env (best-effort) + environment variables, then unmarshals
// into T. Env vars use uppercase form (e.g. AUTH_SECRET_KEY).
//
// The serviceName fallback is applied if the env var is unset.
//
// All `mapstructure`-tagged fields on T (and squash-embedded structs) are
// auto-bound to their uppercase env equivalent.
func LoadConfig[T any](serviceName string) (T, error) {
	var cfg T

	v := viper.New()
	v.SetConfigName(".env")
	v.SetConfigType("env")
	v.AddConfigPath(".")
	v.AddConfigPath("/app")
	v.AutomaticEnv()
	v.SetEnvKeyReplacer(strings.NewReplacer(".", "_"))

	// Sensible defaults for every BaseSettings key. SetDefault also registers
	// the key with viper so AutomaticEnv resolves it.
	v.SetDefault("service_name", serviceName)
	v.SetDefault("environment", "development")
	v.SetDefault("log_level", "info")
	v.SetDefault("cors_origins", []string{})
	v.SetDefault("auth_secret_key", "")
	v.SetDefault("auth_algorithm", "HS256")
	v.SetDefault("access_token_expire_minutes", 30)
	v.SetDefault("refresh_token_expire_days", 7)

	// Bind every mapstructure-tagged field on T to its uppercase env var.
	// Lets services extend BaseSettings with their own fields without
	// having to call BindEnv manually.
	bindEnvsFromStruct(v, reflect.TypeOf(cfg))

	// .env file is optional; ignore "not found" but surface other errors.
	if err := v.ReadInConfig(); err != nil {
		var nfe viper.ConfigFileNotFoundError
		if !errors.As(err, &nfe) {
			return cfg, fmt.Errorf("read config: %w", err)
		}
	}

	// CORS_ORIGINS in env arrives as a comma-separated string.
	if raw := v.GetString("cors_origins"); raw != "" && !strings.HasPrefix(raw, "[") {
		parts := strings.Split(raw, ",")
		clean := make([]string, 0, len(parts))
		for _, p := range parts {
			if s := strings.TrimSpace(p); s != "" {
				clean = append(clean, s)
			}
		}
		v.Set("cors_origins", clean)
	}

	if err := v.Unmarshal(&cfg); err != nil {
		return cfg, fmt.Errorf("unmarshal config: %w", err)
	}
	return cfg, nil
}

// bindEnvsFromStruct recursively walks T's `mapstructure` tags and BindEnv
// each one against viper. Handles squash-embedded structs.
func bindEnvsFromStruct(v *viper.Viper, t reflect.Type) {
	if t.Kind() == reflect.Pointer {
		t = t.Elem()
	}
	if t.Kind() != reflect.Struct {
		return
	}
	for i := 0; i < t.NumField(); i++ {
		field := t.Field(i)
		tag := field.Tag.Get("mapstructure")
		if tag == "" || tag == "-" {
			continue
		}
		name, opts, _ := strings.Cut(tag, ",")
		// Embedded struct with `,squash` — recurse.
		if strings.Contains(opts, "squash") || name == "" {
			bindEnvsFromStruct(v, field.Type)
			continue
		}
		_ = v.BindEnv(name)
	}
}

// Validate fails fast on missing required base fields.
func (b BaseSettings) Validate() error {
	if b.ServiceName == "" {
		return errors.New("service_name is required")
	}
	if len(b.AuthSecretKey) < 16 {
		return errors.New("auth_secret_key must be at least 16 characters")
	}
	return nil
}
