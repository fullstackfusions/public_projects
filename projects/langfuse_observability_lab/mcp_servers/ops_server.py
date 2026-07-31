"""MCP server exposing 'ops' tools: order lookup, refunds, arithmetic.

Runs over stdio. The refund tool deliberately raises for one magic order id
(ORD-999) so the demo has a real failure to observe in Langfuse traces,
instead of only ever showing the happy path.
"""
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("ops-server")

_ORDERS = {
    "ORD-100": {"status": "delivered", "amount": 49.99},
    "ORD-200": {"status": "processing", "amount": 129.50},
    "ORD-999": {"status": "delivered", "amount": 899.00},  # refund on this one fails
}


@mcp.tool()
def get_order_status(order_id: str) -> str:
    """Look up the shipping status and amount for an order id, e.g. ORD-100."""
    order = _ORDERS.get(order_id)
    if not order:
        return f"No order found with id '{order_id}'."
    return f"Order {order_id}: status={order['status']}, amount=${order['amount']:.2f}"


@mcp.tool()
def refund_order(order_id: str, amount: float) -> str:
    """Issue a refund for an order id. Fails for orders flagged as high-risk."""
    order = _ORDERS.get(order_id)
    if not order:
        raise ValueError(f"Cannot refund unknown order '{order_id}'.")
    if order_id == "ORD-999":
        # Simulates a downstream payment-provider failure (e.g. fraud hold).
        raise RuntimeError(
            f"Payment provider declined refund for {order_id}: account under fraud review."
        )
    if amount > order["amount"]:
        raise ValueError(
            f"Refund amount ${amount:.2f} exceeds order total ${order['amount']:.2f}."
        )
    return f"Refunded ${amount:.2f} to order {order_id}."


@mcp.tool()
def calculate(expression: str) -> str:
    """Evaluate a simple arithmetic expression, e.g. '129.50 * 0.15'."""
    allowed = set("0123456789.+-*/() ")
    if not set(expression) <= allowed:
        raise ValueError(f"Unsupported characters in expression: {expression!r}")
    return str(eval(expression, {"__builtins__": {}}, {}))  # noqa: S307 - sandboxed charset above


if __name__ == "__main__":
    mcp.run(transport="stdio")
