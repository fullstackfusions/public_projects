// Package migrations embeds the SQL migration files into the binary.
//
// Consumed by cmd/server/main.go via golang-migrate's iofs source.
package migrations

import "embed"

// FS exposes every *.sql sibling to this file.
//
//go:embed *.sql
var FS embed.FS
