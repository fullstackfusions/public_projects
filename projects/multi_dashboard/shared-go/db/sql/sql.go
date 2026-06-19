// Package sql provides a pgx/v5 connection pool factory.
//
// Each Go service constructs one pool at startup and shares it across
// handlers. pgx is connection-pooled and goroutine-safe by default.
//
//	pool, err := sql.NewPool(ctx, cfg.TodoDatabaseURL)
//	defer pool.Close()
package sql

import (
	"context"
	"fmt"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"
)

// NewPool dials Postgres with sensible defaults and verifies connectivity.
//
// `connString` is a libpq-style URL:
//
//	postgres://user:pass@host:5432/dbname?sslmode=disable
func NewPool(ctx context.Context, connString string) (*pgxpool.Pool, error) {
	cfg, err := pgxpool.ParseConfig(connString)
	if err != nil {
		return nil, fmt.Errorf("parse pgx config: %w", err)
	}
	cfg.MaxConns = 10
	cfg.MinConns = 1
	cfg.MaxConnLifetime = time.Hour
	cfg.MaxConnIdleTime = 30 * time.Minute

	pool, err := pgxpool.NewWithConfig(ctx, cfg)
	if err != nil {
		return nil, fmt.Errorf("create pool: %w", err)
	}

	pingCtx, cancel := context.WithTimeout(ctx, 5*time.Second)
	defer cancel()
	if err := pool.Ping(pingCtx); err != nil {
		pool.Close()
		return nil, fmt.Errorf("ping postgres: %w", err)
	}
	return pool, nil
}
