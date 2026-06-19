package handlers

import (
	"encoding/json"
	"log"
	"strings"
	"time"

	"github.com/gofiber/contrib/websocket"
	"github.com/gofiber/fiber/v2"
	"github.com/google/uuid"

	"github.com/mihirzz/fullstack_chatbot_llm/backends/chatbot-go/internal/domain"
	"github.com/mihirzz/fullstack_chatbot_llm/backends/chatbot-go/internal/models"
	"github.com/mihirzz/fullstack_chatbot_llm/backends/chatbot-go/internal/store"
)

// RegisterWS mounts the WebSocket chat endpoint.
//
// The WS upgrade check must run before RequireAuth so the upgrade-negotiation
// headers are present when the token is extracted from ?access_token=.
func RegisterWS(app *fiber.App, s *store.Store, authMiddleware fiber.Handler) {
	app.Use("/ws", func(c *fiber.Ctx) error {
		if websocket.IsWebSocketUpgrade(c) {
			return c.Next()
		}
		return fiber.ErrUpgradeRequired
	})
	app.Get("/ws/chat", authMiddleware, websocket.New(wsHandle(s)))
}

func wsHandle(s *store.Store) func(*websocket.Conn) {
	return func(c *websocket.Conn) {
		convID := uuid.New().String()
		log.Printf("ws connected conv=%s", convID)
		defer func() {
			log.Printf("ws disconnected conv=%s", convID)
			c.Close()
		}()

		for {
			_, raw, err := c.ReadMessage()
			if err != nil {
				if websocket.IsCloseError(err, websocket.CloseGoingAway, websocket.CloseNormalClosure) {
					return
				}
				log.Printf("ws read error: %v", err)
				return
			}

			var req models.ChatRequest
			if err := json.Unmarshal(raw, &req); err != nil {
				wsSend(c, models.StatusUpdate{Type: "error", Content: "invalid message format", Timestamp: time.Now().Format(time.RFC3339)})
				continue
			}
			if req.Message == "" {
				wsSend(c, models.StatusUpdate{Type: "error", Content: "empty message", Timestamp: time.Now().Format(time.RFC3339)})
				continue
			}

			id := req.ConversationID
			if id == "" {
				id = convID
			}

			userMsg := models.NewChatMessage("user", req.Message)
			s.AddMessage(id, userMsg)

			wsSend(c, models.StatusUpdate{
				Type:           "received",
				MessageID:      userMsg.ID,
				ConversationID: id,
				Timestamp:      time.Now().Format(time.RFC3339),
			})

			wsProcess(c, s, id)
		}
	}
}

func wsProcess(c *websocket.Conn, s *store.Store, convID string) {
	n := domain.RandomStatusCount()
	for i := 0; i < n; i++ {
		wsSend(c, models.StatusUpdate{
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
		wsSend(c, models.StatusUpdate{
			Type:      "chunk",
			Content:   acc.String(),
			IsFinal:   i == len(words)-1,
			Timestamp: time.Now().Format(time.RFC3339),
		})
		time.Sleep(domain.RandomChunkDelay())
	}

	assistantMsg := models.NewChatMessage("assistant", fullResp)
	s.AddMessage(convID, assistantMsg)

	wsSend(c, models.StatusUpdate{
		Type:           "complete",
		Content:        fullResp,
		MessageID:      assistantMsg.ID,
		ConversationID: convID,
		Timestamp:      time.Now().Format(time.RFC3339),
	})
}

func wsSend(c *websocket.Conn, v any) {
	data, err := json.Marshal(v)
	if err != nil {
		log.Printf("ws marshal error: %v", err)
		return
	}
	if err := c.WriteMessage(websocket.TextMessage, data); err != nil {
		log.Printf("ws write error: %v", err)
	}
}
