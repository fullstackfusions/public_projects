from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from shared.auth import get_current_user_factory
from shared.logging import get_logger

from ..config import get_settings
from ..schemas import CreateOrderRequest, CreateOrderResponse, OrderCreatedEventV1, OrderCreatedOrder  # type: ignore[attr-defined]

logger = get_logger(__name__)

router = APIRouter(tags=["orders"])

get_current_user = get_current_user_factory(
    secret_provider=lambda: get_settings().auth_secret_key,
    algorithm="HS256",
)


@router.post("/orders", response_model=CreateOrderResponse, status_code=201)
async def create_order(
    req: CreateOrderRequest,
    request: Request,
    _user=Depends(get_current_user),
) -> CreateOrderResponse:
    producer = request.app.state.kafka_producer
    order_id = f"ord_{req.user_id}_{req.amount_cents}"

    event = OrderCreatedEventV1(
        order=OrderCreatedOrder(
            order_id=order_id,
            user_id=req.user_id,
            amount_cents=req.amount_cents,
        )
    )

    await producer.send_and_wait(
        get_settings().topic_orders_created,
        event.model_dump(),
    )

    logger.info("Published OrderCreatedEvent", extra={"order_id": order_id})
    return CreateOrderResponse(order_id=order_id, status="created")
