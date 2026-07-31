"""MCP server exposing 'knowledge' tools: doc search, ticket lookup.

Runs over stdio. Backs the support subagent in the demo.
"""
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("knowledge-server")

_DOCS = {
    "return policy": "Items can be returned within 30 days of delivery for a full refund.",
    "shipping times": "Standard shipping takes 3-5 business days; express takes 1-2.",
    "password reset": "Go to Account -> Security -> Reset Password, then check your email.",
}

_TICKETS = {
    "TCK-1": {"subject": "Late delivery", "status": "open"},
    "TCK-2": {"subject": "Wrong item received", "status": "resolved"},
}


@mcp.tool()
def search_docs(query: str) -> str:
    """Search the internal knowledge base for a topic, e.g. 'return policy'."""
    query_lower = query.lower()
    hits = [text for topic, text in _DOCS.items() if topic in query_lower or query_lower in topic]
    if not hits:
        return f"No knowledge base articles matched '{query}'."
    return "\n".join(hits)


@mcp.tool()
def lookup_ticket(ticket_id: str) -> str:
    """Look up a support ticket by id, e.g. TCK-1."""
    ticket = _TICKETS.get(ticket_id)
    if not ticket:
        return f"No ticket found with id '{ticket_id}'."
    return f"Ticket {ticket_id}: subject='{ticket['subject']}', status={ticket['status']}"


if __name__ == "__main__":
    mcp.run(transport="stdio")
