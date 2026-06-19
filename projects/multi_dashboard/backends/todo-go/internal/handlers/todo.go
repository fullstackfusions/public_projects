package handlers

import (
	"strconv"
	"time"

	"github.com/gofiber/fiber/v2"
	"github.com/google/uuid"

	apperrors "github.com/mihirzz/chatbot-shared-go/errors"

	"github.com/mihirzz/fullstack_chatbot_llm/backends/todo-go/internal/repo"
	"github.com/mihirzz/fullstack_chatbot_llm/backends/todo-go/internal/service"
)

// todoPayload is the shared body shape for POST/PUT/PATCH.
type todoPayload struct {
	Title       *string    `json:"title"`
	Description *string    `json:"description"`
	Completed   *bool      `json:"completed"`
	DueDate     *time.Time `json:"due_date"`
}

// RegisterTodos mounts /todos routes behind the provided auth middleware.
func RegisterTodos(app *fiber.App, svc *service.TodoService, requireAuth fiber.Handler) {
	g := app.Group("/todos", requireAuth)

	g.Get("/", func(c *fiber.Ctx) error {
		filter := repo.ListFilter{}
		if raw := c.Query("completed"); raw != "" {
			b, err := strconv.ParseBool(raw)
			if err != nil {
				return apperrors.NewValidation("invalid completed filter", map[string]any{"value": raw})
			}
			filter.Completed = &b
		}
		todos, err := svc.List(c.UserContext(), filter)
		if err != nil {
			return err
		}
		return c.JSON(todos)
	})

	g.Post("/", func(c *fiber.Ctx) error {
		var p todoPayload
		if err := c.BodyParser(&p); err != nil {
			return apperrors.NewValidation("invalid request body", map[string]any{"reason": err.Error()})
		}
		title := ""
		if p.Title != nil {
			title = *p.Title
		}
		desc := ""
		if p.Description != nil {
			desc = *p.Description
		}
		completed := false
		if p.Completed != nil {
			completed = *p.Completed
		}
		t, err := svc.Create(c.UserContext(), repo.CreateInput{
			Title:       title,
			Description: desc,
			Completed:   completed,
			DueDate:     p.DueDate,
		})
		if err != nil {
			return err
		}
		return c.Status(fiber.StatusCreated).JSON(t)
	})

	g.Get("/:id", func(c *fiber.Ctx) error {
		id, err := parseID(c.Params("id"))
		if err != nil {
			return err
		}
		t, err := svc.Get(c.UserContext(), id)
		if err != nil {
			return err
		}
		return c.JSON(t)
	})

	g.Put("/:id", func(c *fiber.Ctx) error {
		id, err := parseID(c.Params("id"))
		if err != nil {
			return err
		}
		var p todoPayload
		if err := c.BodyParser(&p); err != nil {
			return apperrors.NewValidation("invalid request body", map[string]any{"reason": err.Error()})
		}
		title := ""
		if p.Title != nil {
			title = *p.Title
		}
		desc := ""
		if p.Description != nil {
			desc = *p.Description
		}
		completed := false
		if p.Completed != nil {
			completed = *p.Completed
		}
		t, err := svc.Update(c.UserContext(), id, repo.UpdateInput{
			Title:       title,
			Description: desc,
			Completed:   completed,
			DueDate:     p.DueDate,
		})
		if err != nil {
			return err
		}
		return c.JSON(t)
	})

	g.Patch("/:id", func(c *fiber.Ctx) error {
		id, err := parseID(c.Params("id"))
		if err != nil {
			return err
		}
		// Preserve "field absent" vs "field present with value" semantics by
		// re-parsing the raw body as a map.
		raw := map[string]any{}
		if err := c.BodyParser(&raw); err != nil {
			return apperrors.NewValidation("invalid request body", map[string]any{"reason": err.Error()})
		}
		var p todoPayload
		if err := c.BodyParser(&p); err != nil {
			return apperrors.NewValidation("invalid request body", map[string]any{"reason": err.Error()})
		}
		in := repo.PatchInput{
			Title:       p.Title,
			Description: p.Description,
			Completed:   p.Completed,
		}
		// due_date present in JSON (even as null) → caller wants to set it.
		if _, ok := raw["due_date"]; ok {
			in.SetDueDate = true
			in.DueDate = p.DueDate
		}
		t, err := svc.Patch(c.UserContext(), id, in)
		if err != nil {
			return err
		}
		return c.JSON(t)
	})

	g.Delete("/:id", func(c *fiber.Ctx) error {
		id, err := parseID(c.Params("id"))
		if err != nil {
			return err
		}
		if err := svc.Delete(c.UserContext(), id); err != nil {
			return err
		}
		return c.SendStatus(fiber.StatusNoContent)
	})
}

func parseID(s string) (uuid.UUID, error) {
	id, err := uuid.Parse(s)
	if err != nil {
		return uuid.Nil, apperrors.NewValidation("invalid id", map[string]any{"id": s})
	}
	return id, nil
}
