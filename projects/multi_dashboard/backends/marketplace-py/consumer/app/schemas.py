"""Pydantic schemas for event validation - matches parent service schemas."""
from pydantic import BaseModel, Field


class OrderCreatedOrder(BaseModel):
    """Order data within OrderCreatedEvent."""
    order_id: str = Field(..., description="Unique order identifier")
    user_id: str = Field(..., description="User who created the order")
    amount_cents: int = Field(..., description="Order amount in cents")


class OrderCreatedEventV1(BaseModel):
    """Event schema for orders.created topic.

    This is the event contract that payment service validates against.
    Must match the schema published by marketplace-api service.
    """
    order: OrderCreatedOrder = Field(..., description="Order details")
