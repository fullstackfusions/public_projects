package models

import (
	"time"

	"github.com/google/uuid"
)

// ChatMessage represents a single chat message.
type ChatMessage struct {
	ID        string  `json:"id"`
	Role      string  `json:"role"` // "user" or "assistant"
	Content   string  `json:"content"`
	Timestamp string  `json:"timestamp"`
	Status    *string `json:"status,omitempty"`
}

// ChatRequest is the incoming chat payload.
type ChatRequest struct {
	Message        string `json:"message"`
	ConversationID string `json:"conversation_id,omitempty"`
}

// ChatResponse is the REST sync-chat response.
type ChatResponse struct {
	Message        ChatMessage `json:"message"`
	ConversationID string      `json:"conversation_id"`
}

// StatusUpdate is a real-time progress event (WS / SSE).
type StatusUpdate struct {
	Type           string `json:"type"` // received | status | chunk | complete | error
	Status         string `json:"status,omitempty"`
	Content        string `json:"content,omitempty"`
	Progress       int    `json:"progress,omitempty"`
	MessageID      string `json:"message_id,omitempty"`
	ConversationID string `json:"conversation_id,omitempty"`
	IsFinal        bool   `json:"is_final,omitempty"`
	Timestamp      string `json:"timestamp"`
}

// AsyncResponse is the immediate reply for async REST requests.
type AsyncResponse struct {
	RequestID      string `json:"request_id"`
	ConversationID string `json:"conversation_id"`
	Status         string `json:"status"`
	Timestamp      string `json:"timestamp"`
}

// PendingResponse stores async request state for polling.
type PendingResponse struct {
	Status         string            `json:"status"`
	Statuses       []StatusUpdateLog `json:"statuses"`
	ConversationID string            `json:"conversation_id"`
	Response       *ChatMessage      `json:"response,omitempty"`
	Error          string            `json:"error,omitempty"`
	CreatedAt      string            `json:"created_at"`
}

// StatusUpdateLog is a single entry in the async status history.
type StatusUpdateLog struct {
	Status    string `json:"status"`
	Progress  int    `json:"progress"`
	Timestamp string `json:"timestamp"`
}

// NewChatMessage creates a message with a generated UUID and RFC3339 timestamp.
func NewChatMessage(role, content string) ChatMessage {
	return ChatMessage{
		ID:        uuid.New().String(),
		Role:      role,
		Content:   content,
		Timestamp: time.Now().Format(time.RFC3339),
	}
}

// NewStatusUpdate creates a StatusUpdate with the current timestamp.
func NewStatusUpdate(updateType string) StatusUpdate {
	return StatusUpdate{
		Type:      updateType,
		Timestamp: time.Now().Format(time.RFC3339),
	}
}
