from __future__ import annotations

import random

RANDOM_RESPONSES = [
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
]

THINKING_STATUSES = [
    "Thinking...",
    "Processing your question...",
    "Analyzing the query...",
    "Working on it...",
    "Consulting knowledge base...",
    "Neural networks activating...",
    "Generating insights...",
    "Computing response...",
]

ADDITIONAL_SENTENCES = [
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
]


def generate_random_response() -> str:
    base = random.choice(RANDOM_RESPONSES)
    num_extra = random.randint(1, 4)
    extra = random.sample(ADDITIONAL_SENTENCES, min(num_extra, len(ADDITIONAL_SENTENCES)))
    return base + " " + " ".join(extra)


def get_random_delay() -> float:
    return random.uniform(0.5, 3.0)


def get_random_status() -> str:
    return random.choice(THINKING_STATUSES)


def get_random_chunk_delay() -> float:
    return random.uniform(0.05, 0.2)
