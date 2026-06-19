// Package store provides thread-safe in-memory storage for chat conversations.
package store

import (
	"sync"

	"github.com/mihirzz/fullstack_chatbot_llm/backends/chatbot-go/internal/models"
)

// Store holds conversations and pending async responses.
type Store struct {
	conversations    map[string][]models.ChatMessage
	pendingResponses map[string]*models.PendingResponse
	mu               sync.RWMutex
}

// New creates an initialised Store.
func New() *Store {
	return &Store{
		conversations:    make(map[string][]models.ChatMessage),
		pendingResponses: make(map[string]*models.PendingResponse),
	}
}

// AddMessage appends a message to the conversation.
func (s *Store) AddMessage(conversationID string, message models.ChatMessage) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.conversations[conversationID] = append(s.conversations[conversationID], message)
}

// GetConversation retrieves all messages for a conversation.
func (s *Store) GetConversation(conversationID string) ([]models.ChatMessage, bool) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	msgs, ok := s.conversations[conversationID]
	return msgs, ok
}

// DeleteConversation removes a conversation.
func (s *Store) DeleteConversation(conversationID string) {
	s.mu.Lock()
	defer s.mu.Unlock()
	delete(s.conversations, conversationID)
}

// SetPendingResponse stores a pending async response.
func (s *Store) SetPendingResponse(requestID string, pending *models.PendingResponse) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.pendingResponses[requestID] = pending
}

// GetPendingResponse retrieves a pending async response.
func (s *Store) GetPendingResponse(requestID string) (*models.PendingResponse, bool) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	p, ok := s.pendingResponses[requestID]
	return p, ok
}

// UpdatePendingStatus appends a status log entry to the pending response.
func (s *Store) UpdatePendingStatus(requestID string, status models.StatusUpdateLog) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if p, ok := s.pendingResponses[requestID]; ok {
		p.Statuses = append(p.Statuses, status)
		p.Status = "processing"
	}
}

// CompletePendingResponse marks a pending response as complete.
func (s *Store) CompletePendingResponse(requestID string, message *models.ChatMessage) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if p, ok := s.pendingResponses[requestID]; ok {
		p.Status = "complete"
		p.Response = message
	}
}

// ErrorPendingResponse marks a pending response as errored.
func (s *Store) ErrorPendingResponse(requestID, errorMsg string) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if p, ok := s.pendingResponses[requestID]; ok {
		p.Status = "error"
		p.Error = errorMsg
	}
}
