// Package models holds the wire types for the todo resource.
package models

import (
	"time"

	"github.com/google/uuid"
)

// Todo is the canonical record shape returned to clients.
type Todo struct {
	ID          uuid.UUID  `json:"id"`
	Title       string     `json:"title"`
	Description string     `json:"description"`
	Completed   bool       `json:"completed"`
	DueDate     *time.Time `json:"due_date"`
	CreatedAt   time.Time  `json:"created_at"`
	UpdatedAt   time.Time  `json:"updated_at"`
}
