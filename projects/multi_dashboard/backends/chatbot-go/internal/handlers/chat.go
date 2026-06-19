package handlers

import (
	"bufio"
	"strings"
	"time"

	"github.com/gofiber/fiber/v2"
	"github.com/google/uuid"

	"github.com/mihirzz/fullstack_chatbot_llm/backends/chatbot-go/internal/domain"
	"github.com/mihirzz/fullstack_chatbot_llm/backends/chatbot-go/internal/models"
	"github.com/mihirzz/fullstack_chatbot_llm/backends/chatbot-go/internal/store"
)

// RegisterChat mounts all REST + SSE chat routes under a RequireAuth group.
//
//   - POST   /api/chat              – synchronous chat
//   - POST   /api/chat/async        – async chat (returns request_id)
//   - GET    /api/chat/status/:id   – poll async status
//   - GET    /api/chat/stream       – SSE streaming chat (POST body via query / JSON)
//   - GET    /api/conversations/:id – conversation history
//   - DELETE /api/conversations/:id – clear conversation
func RegisterChat(app *fiber.App, s *store.Store, authMiddleware fiber.Handler) {
	api := app.Group("/api", authMiddleware)

	api.Post("/chat", syncChat(s))
	api.Post("/chat/async", asyncChat(s))
	api.Get("/chat/status/:request_id", chatStatus(s))
	api.Post("/chat/stream", sseChat(s))
	api.Get("/conversations/:conversation_id", getConversation(s))
	api.Delete("/conversations/:conversation_id", clearConversation(s))
}

func syncChat(s *store.Store) fiber.Handler {
	return func(c *fiber.Ctx) error {
		var req models.ChatRequest
		if err := c.BodyParser(&req); err != nil {
			return fiber.NewError(fiber.StatusBadRequest, "invalid request body")
		}
		if req.Message == "" {
			return fiber.NewError(fiber.StatusBadRequest, "message is required")
		}
		convID := convOrNew(req.ConversationID)

		userMsg := models.NewChatMessage("user", req.Message)
		s.AddMessage(convID, userMsg)

		time.Sleep(domain.RandomDelay() * 2)

		assistantMsg := models.NewChatMessage("assistant", domain.GenerateResponse())
		s.AddMessage(convID, assistantMsg)

		return c.JSON(models.ChatResponse{Message: assistantMsg, ConversationID: convID})
	}
}

func asyncChat(s *store.Store) fiber.Handler {
	return func(c *fiber.Ctx) error {
		var req models.ChatRequest
		if err := c.BodyParser(&req); err != nil {
			return fiber.NewError(fiber.StatusBadRequest, "invalid request body")
		}
		if req.Message == "" {
			return fiber.NewError(fiber.StatusBadRequest, "message is required")
		}
		convID := convOrNew(req.ConversationID)
		reqID := uuid.New().String()

		userMsg := models.NewChatMessage("user", req.Message)
		s.AddMessage(convID, userMsg)
		s.SetPendingResponse(reqID, &models.PendingResponse{
			Status:         "pending",
			Statuses:       []models.StatusUpdateLog{},
			ConversationID: convID,
			CreatedAt:      time.Now().Format(time.RFC3339),
		})

		go processAsync(s, reqID, convID)

		return c.JSON(models.AsyncResponse{
			RequestID:      reqID,
			ConversationID: convID,
			Status:         "processing",
			Timestamp:      time.Now().Format(time.RFC3339),
		})
	}
}

func processAsync(s *store.Store, requestID, convID string) {
	n := domain.RandomStatusCount()
	for i := 0; i < n; i++ {
		s.UpdatePendingStatus(requestID, models.StatusUpdateLog{
			Status:    domain.RandomStatus(),
			Progress:  int(float64(i+1) / float64(n) * 100),
			Timestamp: time.Now().Format(time.RFC3339),
		})
		time.Sleep(domain.RandomDelay() / time.Duration(n))
	}
	msg := models.NewChatMessage("assistant", domain.GenerateResponse())
	s.AddMessage(convID, msg)
	s.CompletePendingResponse(requestID, &msg)
}

func chatStatus(s *store.Store) fiber.Handler {
	return func(c *fiber.Ctx) error {
		pending, ok := s.GetPendingResponse(c.Params("request_id"))
		if !ok {
			return fiber.NewError(fiber.StatusNotFound, "request not found")
		}
		return c.JSON(pending)
	}
}

func sseChat(s *store.Store) fiber.Handler {
	return func(c *fiber.Ctx) error {
		var req models.ChatRequest
		if err := c.BodyParser(&req); err != nil {
			return fiber.NewError(fiber.StatusBadRequest, "invalid request body")
		}
		if req.Message == "" {
			return fiber.NewError(fiber.StatusBadRequest, "message is required")
		}
		convID := convOrNew(req.ConversationID)

		userMsg := models.NewChatMessage("user", req.Message)
		s.AddMessage(convID, userMsg)

		c.Set("Content-Type", "text/event-stream")
		c.Set("Cache-Control", "no-cache")
		c.Set("Connection", "keep-alive")
		c.Set("X-Accel-Buffering", "no")

		c.Context().SetBodyStreamWriter(func(w *bufio.Writer) {
			sseSend(w, "received", models.StatusUpdate{
				Type:           "received",
				MessageID:      userMsg.ID,
				ConversationID: convID,
				Timestamp:      time.Now().Format(time.RFC3339),
			})

			n := domain.RandomStatusCount()
			for i := 0; i < n; i++ {
				sseSend(w, "status", models.StatusUpdate{
					Type:      "status",
					Status:    domain.RandomStatus(),
					Progress:  int(float64(i+1) / float64(n) * 100),
					Timestamp: time.Now().Format(time.RFC3339),
				})
				time.Sleep(domain.RandomDelay() / time.Duration(n))
			}

			fullResp := domain.GenerateResponse()
			words := domain.SplitWords(fullResp)
			var acc strings.Builder
			for i, word := range words {
				if acc.Len() > 0 {
					acc.WriteString(" ")
				}
				acc.WriteString(word)
				sseSend(w, "chunk", models.StatusUpdate{
					Type:      "chunk",
					Content:   acc.String(),
					IsFinal:   i == len(words)-1,
					Timestamp: time.Now().Format(time.RFC3339),
				})
				time.Sleep(domain.RandomChunkDelay())
			}

			assistantMsg := models.NewChatMessage("assistant", fullResp)
			s.AddMessage(convID, assistantMsg)

			sseSend(w, "complete", models.StatusUpdate{
				Type:           "complete",
				Content:        fullResp,
				MessageID:      assistantMsg.ID,
				ConversationID: convID,
				Timestamp:      time.Now().Format(time.RFC3339),
			})
		})
		return nil
	}
}

func getConversation(s *store.Store) fiber.Handler {
	return func(c *fiber.Ctx) error {
		convID := c.Params("conversation_id")
		msgs, ok := s.GetConversation(convID)
		if !ok {
			return fiber.NewError(fiber.StatusNotFound, "conversation not found")
		}
		return c.JSON(fiber.Map{"conversation_id": convID, "messages": msgs})
	}
}

func clearConversation(s *store.Store) fiber.Handler {
	return func(c *fiber.Ctx) error {
		s.DeleteConversation(c.Params("conversation_id"))
		return c.JSON(fiber.Map{"message": "conversation cleared"})
	}
}

func convOrNew(id string) string {
	if id == "" {
		return uuid.New().String()
	}
	return id
}
