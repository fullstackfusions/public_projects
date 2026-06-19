// Package service holds the business logic for todos.
//
// Handlers call into this package; this package calls repo. Repo errors are
// mapped to shared AppError so the Fiber error handler can render the
// canonical envelope.
package service

import (
	"context"
	"errors"
	"strings"

	"github.com/google/uuid"

	apperrors "github.com/mihirzz/chatbot-shared-go/errors"

	"github.com/mihirzz/fullstack_chatbot_llm/backends/todo-go/internal/models"
	"github.com/mihirzz/fullstack_chatbot_llm/backends/todo-go/internal/repo"
)

// TodoService is the boundary handlers depend on.
type TodoService struct {
	repo *repo.TodoRepo
}

// NewTodoService builds a service over a repo.
func NewTodoService(r *repo.TodoRepo) *TodoService { return &TodoService{repo: r} }

func (s *TodoService) List(ctx context.Context, f repo.ListFilter) ([]models.Todo, error) {
	out, err := s.repo.List(ctx, f)
	if err != nil {
		return nil, apperrors.NewInternal("failed to list todos", nil)
	}
	return out, nil
}

func (s *TodoService) Get(ctx context.Context, id uuid.UUID) (models.Todo, error) {
	t, err := s.repo.Get(ctx, id)
	if errors.Is(err, repo.ErrNotFound) {
		return models.Todo{}, apperrors.NewNotFound("todo not found", map[string]any{"id": id.String()})
	}
	if err != nil {
		return models.Todo{}, apperrors.NewInternal("failed to fetch todo", nil)
	}
	return t, nil
}

func (s *TodoService) Create(ctx context.Context, in repo.CreateInput) (models.Todo, error) {
	if err := validateTitle(in.Title); err != nil {
		return models.Todo{}, err
	}
	in.Title = strings.TrimSpace(in.Title)
	t, err := s.repo.Create(ctx, in)
	if err != nil {
		return models.Todo{}, apperrors.NewInternal("failed to create todo", nil)
	}
	return t, nil
}

func (s *TodoService) Update(ctx context.Context, id uuid.UUID, in repo.UpdateInput) (models.Todo, error) {
	if err := validateTitle(in.Title); err != nil {
		return models.Todo{}, err
	}
	in.Title = strings.TrimSpace(in.Title)
	t, err := s.repo.Update(ctx, id, in)
	if errors.Is(err, repo.ErrNotFound) {
		return models.Todo{}, apperrors.NewNotFound("todo not found", map[string]any{"id": id.String()})
	}
	if err != nil {
		return models.Todo{}, apperrors.NewInternal("failed to update todo", nil)
	}
	return t, nil
}

func (s *TodoService) Patch(ctx context.Context, id uuid.UUID, in repo.PatchInput) (models.Todo, error) {
	if in.Title != nil {
		if err := validateTitle(*in.Title); err != nil {
			return models.Todo{}, err
		}
		trimmed := strings.TrimSpace(*in.Title)
		in.Title = &trimmed
	}
	t, err := s.repo.Patch(ctx, id, in)
	if errors.Is(err, repo.ErrNotFound) {
		return models.Todo{}, apperrors.NewNotFound("todo not found", map[string]any{"id": id.String()})
	}
	if err != nil {
		return models.Todo{}, apperrors.NewInternal("failed to update todo", nil)
	}
	return t, nil
}

func (s *TodoService) Delete(ctx context.Context, id uuid.UUID) error {
	err := s.repo.Delete(ctx, id)
	if errors.Is(err, repo.ErrNotFound) {
		return apperrors.NewNotFound("todo not found", map[string]any{"id": id.String()})
	}
	if err != nil {
		return apperrors.NewInternal("failed to delete todo", nil)
	}
	return nil
}

func validateTitle(t string) error {
	trimmed := strings.TrimSpace(t)
	if trimmed == "" {
		return apperrors.NewValidation("title is required", nil)
	}
	if len(trimmed) > 200 {
		return apperrors.NewValidation("title exceeds 200 characters", map[string]any{"length": len(trimmed)})
	}
	return nil
}
