export interface Order {
  order_id: string;
  status: string;
}

export interface CreateOrderRequest {
  user_id: string;
  amount_cents: number;
}

export type CreateOrderResponse = Order;
