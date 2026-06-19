"""Pydantic schemas for API contracts and event contracts."""
from pydantic import BaseModel, Field


# HTTP API Contracts (OpenAPI)
class CreateOrderRequest(BaseModel):
    """Request to create a new order."""
    user_id: str = Field(..., description="Unique user identifier")
    amount_cents: int = Field(..., gt=0, description="Order amount in cents")


class CreateOrderResponse(BaseModel):
    """Response after creating an order."""
    order_id: str = Field(..., description="Unique order identifier")
    status: str = Field(..., description="Order status")


# Event Contracts (AsyncAPI)
class OrderCreatedOrder(BaseModel):
    """Order data within OrderCreatedEvent."""
    order_id: str = Field(..., description="Unique order identifier")
    user_id: str = Field(..., description="User who created the order")
    amount_cents: int = Field(..., description="Order amount in cents")


class OrderCreatedEventV1(BaseModel):
    """Event published when an order is created.

    Topic: orders.created
    Version: v1
    Producer: marketplace-api
    Consumers: payment-service, notification-service, analytics-service
    """
    order: OrderCreatedOrder = Field(..., description="Order details")

    class Config:
        json_schema_extra = {
            "example": {
                "order": {
                    "order_id": "ord_user_1_001",
                    "user_id": "user_1",
                    "amount_cents": 1999
                }
            }
        }
