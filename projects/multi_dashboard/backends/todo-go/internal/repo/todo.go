// Package repo provides pgx-backed CRUD for the todos table.
//
// All queries use parameterized SQL — never f-string concat (CWE-89).
// Errors are returned raw (pgx.ErrNoRows surfaces sentinel) — the service
// layer maps them to AppError.
package repo

import (
	"context"
	"errors"
	"time"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"

	"github.com/mihirzz/fullstack_chatbot_llm/backends/todo-go/internal/models"
)

// ErrNotFound is returned when no row matches the lookup.
var ErrNotFound = errors.New("todo not found")

// TodoRepo encapsulates DB access for the todos table.
type TodoRepo struct {
	pool *pgxpool.Pool
}

// NewTodoRepo wires a repo onto a pgx pool.
func NewTodoRepo(pool *pgxpool.Pool) *TodoRepo { return &TodoRepo{pool: pool} }

// ListFilter optionally filters by `completed`.
type ListFilter struct {
	Completed *bool
}

// List returns todos ordered by created_at desc.
func (r *TodoRepo) List(ctx context.Context, f ListFilter) ([]models.Todo, error) {
	const base = `SELECT id, title, description, completed, due_date, created_at, updated_at
	              FROM todos`

	var (
		rows pgx.Rows
		err  error
	)
	if f.Completed != nil {
		rows, err = r.pool.Query(ctx, base+` WHERE completed = $1 ORDER BY created_at DESC`, *f.Completed)
	} else {
		rows, err = r.pool.Query(ctx, base+` ORDER BY created_at DESC`)
	}
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	out := make([]models.Todo, 0)
	for rows.Next() {
		t, err := scanTodo(rows)
		if err != nil {
			return nil, err
		}
		out = append(out, t)
	}
	return out, rows.Err()
}

// Get returns a single todo or ErrNotFound.
func (r *TodoRepo) Get(ctx context.Context, id uuid.UUID) (models.Todo, error) {
	const q = `SELECT id, title, description, completed, due_date, created_at, updated_at
	           FROM todos WHERE id = $1`
	row := r.pool.QueryRow(ctx, q, id)
	t, err := scanTodo(row)
	if errors.Is(err, pgx.ErrNoRows) {
		return models.Todo{}, ErrNotFound
	}
	return t, err
}

// CreateInput is the input shape for Create.
type CreateInput struct {
	Title       string
	Description string
	Completed   bool
	DueDate     *time.Time
}

// Create inserts a row and returns the full record (DB-generated id + timestamps).
func (r *TodoRepo) Create(ctx context.Context, in CreateInput) (models.Todo, error) {
	const q = `INSERT INTO todos (title, description, completed, due_date)
	           VALUES ($1, $2, $3, $4)
	           RETURNING id, title, description, completed, due_date, created_at, updated_at`
	row := r.pool.QueryRow(ctx, q, in.Title, in.Description, in.Completed, in.DueDate)
	return scanTodo(row)
}

// UpdateInput is a full replacement (PUT semantics).
type UpdateInput struct {
	Title       string
	Description string
	Completed   bool
	DueDate     *time.Time
}

// Update fully replaces a row's mutable fields.
func (r *TodoRepo) Update(ctx context.Context, id uuid.UUID, in UpdateInput) (models.Todo, error) {
	const q = `UPDATE todos
	           SET title = $1, description = $2, completed = $3, due_date = $4, updated_at = now()
	           WHERE id = $5
	           RETURNING id, title, description, completed, due_date, created_at, updated_at`
	row := r.pool.QueryRow(ctx, q, in.Title, in.Description, in.Completed, in.DueDate, id)
	t, err := scanTodo(row)
	if errors.Is(err, pgx.ErrNoRows) {
		return models.Todo{}, ErrNotFound
	}
	return t, err
}

// PatchInput holds optional fields (nil = leave unchanged).
type PatchInput struct {
	Title       *string
	Description *string
	Completed   *bool
	DueDate     *time.Time
	// SetDueDate distinguishes "leave alone" (false) from "set to NULL/value" (true).
	SetDueDate bool
}

// Patch applies a partial update via COALESCE-style SQL.
func (r *TodoRepo) Patch(ctx context.Context, id uuid.UUID, in PatchInput) (models.Todo, error) {
	const q = `UPDATE todos SET
	             title       = COALESCE($1, title),
	             description = COALESCE($2, description),
	             completed   = COALESCE($3, completed),
	             due_date    = CASE WHEN $4::boolean THEN $5 ELSE due_date END,
	             updated_at  = now()
	           WHERE id = $6
	           RETURNING id, title, description, completed, due_date, created_at, updated_at`
	row := r.pool.QueryRow(ctx, q, in.Title, in.Description, in.Completed, in.SetDueDate, in.DueDate, id)
	t, err := scanTodo(row)
	if errors.Is(err, pgx.ErrNoRows) {
		return models.Todo{}, ErrNotFound
	}
	return t, err
}

// Delete removes a row. Returns ErrNotFound if no row matched.
func (r *TodoRepo) Delete(ctx context.Context, id uuid.UUID) error {
	const q = `DELETE FROM todos WHERE id = $1`
	tag, err := r.pool.Exec(ctx, q, id)
	if err != nil {
		return err
	}
	if tag.RowsAffected() == 0 {
		return ErrNotFound
	}
	return nil
}

// rowScanner is the smallest interface satisfied by both pgx.Row and pgx.Rows.
type rowScanner interface {
	Scan(dest ...any) error
}

func scanTodo(row rowScanner) (models.Todo, error) {
	var t models.Todo
	err := row.Scan(&t.ID, &t.Title, &t.Description, &t.Completed, &t.DueDate, &t.CreatedAt, &t.UpdatedAt)
	return t, err
}
