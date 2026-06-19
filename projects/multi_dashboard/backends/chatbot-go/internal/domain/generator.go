// Package domain contains the chat response generation logic.
package domain

import (
	"math/rand"
	"strings"
	"time"
)

var randomResponses = []string{
	"That's an interesting question! Let me think about it...",
	"I've analyzed your query and here's what I found.",
	"Based on my understanding, I can suggest the following.",
	"Great question! Here's my perspective on this.",
	"I've processed your request and have some insights to share.",
	"Let me break this down for you step by step.",
	"That's a fascinating topic! Here's what I know.",
	"I've considered various aspects of your question.",
	"Here's a comprehensive answer to your query.",
	"I've done some thinking and here's my response.",
}

var thinkingStatuses = []string{
	"Thinking...",
	"Processing your question...",
	"Analyzing the query...",
	"Working on it...",
	"Consulting knowledge base...",
	"Neural networks activating...",
	"Generating insights...",
	"Computing response...",
}

var additionalSentences = []string{
	"This is particularly relevant in today's context.",
	"Many experts would agree with this perspective.",
	"It's worth considering multiple viewpoints here.",
	"The implications of this are quite significant.",
	"Research has shown interesting patterns in this area.",
	"From a practical standpoint, this makes sense.",
	"The underlying principles are well-established.",
	"This connects to broader themes we often see.",
	"Historical context adds depth to this understanding.",
	"Future developments may change this landscape.",
}

func init() {
	rand.Seed(time.Now().UnixNano()) //nolint:staticcheck
}

// GenerateResponse returns a random multi-sentence bot reply.
func GenerateResponse() string {
	base := randomResponses[rand.Intn(len(randomResponses))]
	numExtra := rand.Intn(4) + 1
	shuffled := make([]string, len(additionalSentences))
	copy(shuffled, additionalSentences)
	rand.Shuffle(len(shuffled), func(i, j int) { shuffled[i], shuffled[j] = shuffled[j], shuffled[i] })
	return base + " " + strings.Join(shuffled[:numExtra], " ")
}

// RandomDelay returns a random processing delay (500ms–3s).
func RandomDelay() time.Duration {
	return time.Duration(500+rand.Intn(2500)) * time.Millisecond
}

// RandomStatus returns a random thinking status string.
func RandomStatus() string {
	return thinkingStatuses[rand.Intn(len(thinkingStatuses))]
}

// RandomChunkDelay returns a random word-streaming delay (50–200ms).
func RandomChunkDelay() time.Duration {
	return time.Duration(50+rand.Intn(150)) * time.Millisecond
}

// RandomStatusCount returns a random number of status updates (2–5).
func RandomStatusCount() int {
	return rand.Intn(4) + 2
}

// SplitWords splits text into individual words.
func SplitWords(text string) []string {
	return strings.Fields(text)
}
